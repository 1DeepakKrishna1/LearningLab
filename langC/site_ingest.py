import argparse
import requests
import xml.etree.ElementTree as ET
import json
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse
from typing import List, Set, Dict
from collections import deque
import re
import json
from markdownify import markdownify as md


# ---------------- CONFIG LLM Open AI----------------
#from langchain_openai import ChatOpenAI

#MODEL = "gpt-4o-mini"
#llm = ChatOpenAI(model=MODEL, temperature=0)


# ---------------- CONFIG LLM GroQ----------------

import os
from langchain_groq import ChatGroq
from dotenv import load_dotenv

load_dotenv()
os.environ["GROQ_API_KEY"] = os.getenv('GROQ_API_KEY')
llm = ChatGroq(model="llama-3.3-70b-versatile", max_tokens=1000, temperature=0)

# ---------------- UTILITIES ----------------

def fetch(url: str) -> str:
    print(f"requesting {url}")
    r = requests.get(url, timeout=50, verify=False)
    r.raise_for_status()
    return r.text


def clean_html(html: str) -> str:
    soup = BeautifulSoup(html, "html.parser")
    for tag in soup(["script", "style", "noscript", "header", "footer", "nav"]):
        tag.decompose()
    return str(soup)


def same_domain(url: str, base: str) -> bool:
    return urlparse(url).netloc == urlparse(base).netloc


def extract_internal_links(html: str, base_url: str) -> Set[str]:
    soup = BeautifulSoup(html, "html.parser")
    links = set()
    for a in soup.find_all("a", href=True):
        full = urljoin(base_url, a["href"])
        if same_domain(full, base_url):
            links.add(full.split("#")[0])
    return links


# ---------------- SITEMAP ----------------

def extract_urls_from_sitemap(base_url: str) -> List[str]:
    sitemap_url = urljoin(base_url, "/sitemap.xml")
    urls = []
    try:
        xml = fetch(sitemap_url)
        root = ET.fromstring(xml)
        for loc in root.iter("{http://www.sitemaps.org/schemas/sitemap/0.9}loc"):
            urls.append(loc.text.strip())
    except Exception as e:
        print(f"Exceptiion in extract_urls_from_sitemap::: {e}")
        pass
    return urls


# ---------------- LLM URL EXTRACTION ----------------

def extract_urls_with_llm(html: str, base_url: str) -> List[str]:
    prompt = f"""
    Given the following information about a website, extract ALL publicly accessible page URLs.

#Website Base URL:
{base_url}

#Homepage HTML:
{html[:12000]}


#Available Inputs (may include one or more):
1. Homepage HTML
2. Navigation menu HTML
3. Footer HTML
4. Known internal links
5. Sitemap.xml content (if available)

#Instructions:
- Extract ALL internal page URLs belonging to the same domain
- Include pages such as:
  - Home
  - About / Company
  - Services / Products
  - Solutions
  - Projects / Case Studies
  - Blog / Articles
  - Careers
  - Team
  - Contact
  - Legal pages (Privacy, Terms, etc.)
  - Demo / Tool / Utility pages
- Include static `.html` pages if present
- URLs may be relative or absolute

#Strict Rules:
- Exclude external domains
- Exclude images, CSS, JS, PDFs, videos
- Exclude anchors (#)
- Do NOT hallucinate URLs
- Only include URLs that are reasonably discoverable from provided inputs

#Output Format (STRICT):
Return ONLY a JSON array of URLs.
Return JSON: [{{  \"url\": \"...\" }} ]

"""
    response = llm.invoke(prompt).content.strip()
    try:
        urls = re.findall(r'"url"\s*:\s*"([^"]+)"', response)

        #urls = eval(response) if response.startswith("[") else []
    except Exception:
        urls = []

    resolved = []
    for u in urls:
        full = urljoin(base_url, u)
        if same_domain(full, base_url):
            resolved.append(full)
    return resolved


# ---------------- LLM MARKDOWN EXTRACTION ----------------

def extract_markdown_with_llm(html: str, url: str) -> str:
    prompt = f"""
Extract meaningful human-readable content and convert it to Markdown.

Rules:
- Preserve headings, lists, tables
- Remove nav/footer
- No hallucination
- Markdown ONLY

Page URL: {url}

HTML:
{html[:12000]}
"""
    return llm.invoke(prompt).content.strip()


# ---------------- LLM KNOWLEDGE GRAPH ----------------

def generate_knowledge_graph(markdown: str) -> Dict:
    prompt = f"""
create knowledge graph in json format from the markdown content

### MARKDOWN CONTENT:
{{markdown}}
"""
    response = llm.invoke(prompt).content.strip()
    try:
        return json.loads(response)
    except Exception as e:
        print(f"Error parsing JSON: {e}")
        return {"entities": [], "relationships": []}


# ---------------- RECURSIVE CRAWL ----------------

def crawl_with_depth(start_urls: Set[str], base_url: str, depth: int) -> Set[str]:
    visited = set()
    queue = deque([(url, 0) for url in start_urls])

    while queue:
        url, level = queue.popleft()
        if url in visited or level > depth:
            continue

        visited.add(url)

        try:
            html = fetch(url)
            if level < depth:
                links = extract_internal_links(html, base_url)
                for link in links:
                    if link not in visited:
                        queue.append((link, level + 1))
        except Exception:
            pass

    return visited


# ---------------- PIPELINE ----------------

def ingest_website(base_url: str, output_file: str, depth: int, kg: bool):
    urls = set()

    print("🔍 Sitemap discovery...")
    urls.update(extract_urls_from_sitemap(base_url))
    print(f"sitemap.xml: {len(urls)} URLs")
    print(urls)

    if(len(urls) <= 5):
        print("🤖 LLM homepage discovery...")
        homepage_html = clean_html(fetch(base_url))
        urls.update(extract_urls_with_llm(homepage_html, base_url))

        print(f"🔁 Recursive crawling (depth={depth})...")
        urls = crawl_with_depth(urls, base_url, depth)

    print(f"🤖 TOTAL URLS...")
    #print(urls)
    print(f"📄 Total pages: {len(urls)}")

    all_markdown = ""

    mdExists = False
    if os.path.exists(output_file):
        mdExists = True
        print(f"File {output_file} already exists. Skipping ingestion.")

    if not mdExists:
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(f"# Website Content Export\n\nSource: {base_url}\n")

            for idx, url in enumerate(sorted(urls), 1):
                print(f"({idx}/{len(urls)}) {url}")
                try:
                    html = clean_html(fetch(url))
                    markdown_content = md(html, heading_style="ATX")
                    
                    '''
                    markdown_content = extract_markdown_with_llm(html, url)
                    '''
                    
                    all_markdown += "\n" + markdown_content
                    f.write(f"\n\n---\n\n## 🔗 {url}\n\n{markdown_content}")

                except Exception as e:
                    f.write(f"\n\n---\n\n## 🔗 {url}\n\n⚠️ Failed\n")
                    print(f"\nFailed to fetch & MD convertion {url}\n Exception Message {e}")

    if kg:
        print("🧠 Generating Knowledge Graph...")
        if mdExists:
            print(f"File {output_file} already exists. Reading it.")
            with open(output_file, "r", encoding="utf-8") as f:
                all_markdown = f.read()

        kg_data = generate_knowledge_graph(all_markdown)
        kg_file = output_file.replace(".md", ".kg.json")
        with open(kg_file, "w", encoding="utf-8") as f:
            json.dump(kg_data, f, indent=2)
        print(f"✅ Knowledge Graph saved to {kg_file}")

    print(f"\n✅ Markdown saved to {output_file}")


# ---------------- CLI ----------------

def main():
    parser = argparse.ArgumentParser("LLM-powered website ingestion CLI")

    ingest = parser.add_subparsers(dest="command").add_parser("ingest")
    ingest.add_argument("url", help="Base website URL")
    ingest.add_argument("--out", default="output.md", help="Output markdown file")
    ingest.add_argument("--depth", type=int, default=0, help="Crawl depth")
    ingest.add_argument("--kg", action="store_true", help="Generate Knowledge Graph")

    args = parser.parse_args()

    if args.command == "ingest":
        ingest_website(args.url, args.out, args.depth, args.kg)
    else:
        parser.print_help()
        #ingest_website("https://www.aisalanalytics.in/", "output.md", 3, False)
        #ingest_website("https://www.jindalpanther.com/", "output.md", 5, False)
        ingest_website("https://jindalpanthercement.com/", "output.md", 5, False)


if __name__ == "__main__":
    main()
