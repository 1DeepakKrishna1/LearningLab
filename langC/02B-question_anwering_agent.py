from langchain_openai import ChatOpenAI
from groq import Groq
from langchain_groq import ChatGroq
from langchain_core.runnables.history import RunnableWithMessageHistory
#from langchain.memory import ChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory

from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.prompts import PromptTemplate
import os
from dotenv import load_dotenv
import json
import re



load_dotenv()

os.environ["GROQ_API_KEY"] = os.getenv('GROQ_API_KEY')


llm = ChatGroq(model="llama-3.3-70b-versatile", max_tokens=1000, temperature=0)

# Path to your JSON file
file_path = 'original.md'


def load_markdown(file_path):
    with open(file_path, 'r', encoding='utf-8') as f:
        return f.readlines()

def save_markdown(file_path, lines):
    with open(file_path, 'w', encoding='utf-8') as f:
        f.writelines(lines)

def normalize_line(line):
    # Remove extra spaces, lowercase, strip punctuation for better matching
    return re.sub(r'[^\w\s]', '', line.strip().lower())

def is_image_line(line):
    # Matches Markdown image syntax or HTML <img> tags
    markdown_img = re.search(r'!\[.*?\]\(.*?\)', line)
    html_img = re.search(r'<img\s+[^>]*src=["\'].*?["\']', line, re.IGNORECASE)
    return bool(markdown_img or html_img)


def deduplicate_lines(lines):
    seen = set()
    deduped = []
    for line in lines:
        if is_image_line(line):
            continue  # Skip image lines

        norm = normalize_line(line)
        if norm and norm not in seen:
            deduped.append(line)
            seen.add(norm)
    return deduped

def truncate_after_end_marker(lines, marker="End Of ReportXYZ"):
    truncated = []
    for line in lines:
        if marker.lower() in line.lower():
            truncated.append(line)
            break
        truncated.append(line)
    return truncated


def reduce_markdown_file(input_path, output_path):
    original_lines = load_markdown(input_path)
    truncated_lines = truncate_after_end_marker(original_lines)
    cleaned_lines = deduplicate_lines(truncated_lines)
    save_markdown(output_path, cleaned_lines)
    print(f"Reduced file saved to: {output_path}")
    print(f"Original lines: {len(original_lines)} → Deduplicated: {len(cleaned_lines)}")


if os.path.exists('cleaned.md'):
    print("File exists.")
else:
    print("File does not exist.")
    reduce_markdown_file('soni.md', 'cleaned.md')

file_path = 'cleaned.md'

# Read and store JSON content as a string
with open(file_path, 'r', encoding='utf-8') as file:
    md_string = file.read()


template = """
You are a highly experienced medical doctor with over 20 years of clinical expertise in internal medicine, diagnostics, and interpreting complex medical test reports.

The following markdown file contains structured medical data, including lab results, imaging summaries, patient vitals, and diagnostic notes. Your task is to:

1. **Review the content thoroughly** as if you are evaluating a real patient case.
2. **Provide a concise, expert-level summary** of the findings.
3. Highlight any **abnormalities, clinical concerns, or patterns** that require attention.
4. Suggest **possible diagnoses or next steps** based on the data, using your medical judgment.
5. Keep your tone **professional, precise, and medically authoritative**.

Respond only with your expert interpretation. Do not restate the raw data unless necessary for clarity.

Here is the content of the markdown file:

{md_string}

User's question: {question}

Please provide a clear and concise answer:
"""

#filled_prompt = template.format(json_string=json.dumps(json_string, indent=2))


prompt = PromptTemplate(template=template, input_variables=["question"])

print(prompt.format( md_string=md_string, question="What is the name of the patient?"))

print("*****************************************************************")

qa_chain = prompt | llm

def get_answer(question, md_string=md_string):
    """
    Get an answer to the given question using the QA chain.
    """
    input_variables = {"question": question, "md_string": md_string}
    response = qa_chain.invoke(input_variables).content
    return response

question = "What is the name of the patient?"
answer = get_answer(question)
print(f"Question: {question}")
print(f"Answer: {answer}")

user_question = input("Enter your question: ")
user_answer = get_answer(user_question)
print(f"Answer: {user_answer}")