"""Turn raw HTML into clean text, a title, and outbound links."""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from urllib.parse import urldefrag, urljoin, urlparse

from bs4 import BeautifulSoup

_STRIP_TAGS = ["script", "style", "noscript", "template", "svg", "iframe"]
_BOILERPLATE_TAGS = ["nav", "header", "footer", "aside", "form"]
_WS = re.compile(r"[ \t\f\v]+")
_MULTI_NL = re.compile(r"\n{3,}")


@dataclass
class ExtractedPage:
    title: str
    text: str
    links: list[str] = field(default_factory=list)
    headings: list[str] = field(default_factory=list)


def _clean_text(node) -> str:
    text = node.get_text(separator="\n")
    lines = [_WS.sub(" ", ln).strip() for ln in text.splitlines()]
    lines = [ln for ln in lines if ln]
    return _MULTI_NL.sub("\n\n", "\n".join(lines)).strip()


def _pick_main(soup: BeautifulSoup):
    """Prefer the semantic main content region when present."""
    for selector in ("main", "article", '[role="main"]', "#content", "#main", ".content", ".main"):
        node = soup.select_one(selector)
        if node and len(node.get_text(strip=True)) > 200:
            return node
    return soup.body or soup


def extract(html: str, base_url: str) -> ExtractedPage:
    soup = BeautifulSoup(html, "lxml")

    title = ""
    if soup.title and soup.title.string:
        title = soup.title.string.strip()
    if not title:
        h1 = soup.find("h1")
        if h1:
            title = h1.get_text(strip=True)
    title = title or base_url

    # Collect links from the full document before we strip boilerplate.
    links: list[str] = []
    for a in soup.find_all("a", href=True):
        href = a["href"].strip()
        if not href or href.startswith(("#", "mailto:", "tel:", "javascript:")):
            continue
        absolute, _ = urldefrag(urljoin(base_url, href))
        if urlparse(absolute).scheme in ("http", "https"):
            links.append(absolute)

    for tag in soup(_STRIP_TAGS):
        tag.decompose()

    main = _pick_main(soup)
    headings = [h.get_text(strip=True) for h in main.find_all(["h1", "h2", "h3"]) if h.get_text(strip=True)]

    # Remove boilerplate only from a working copy of the main region.
    for tag in main.find_all(_BOILERPLATE_TAGS):
        tag.decompose()

    text = _clean_text(main)
    # Dedupe consecutive identical links, preserving order.
    seen: set[str] = set()
    uniq_links = [u for u in links if not (u in seen or seen.add(u))]

    return ExtractedPage(title=title, text=text, links=uniq_links, headings=headings)
