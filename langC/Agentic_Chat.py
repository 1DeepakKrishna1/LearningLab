import os
import json

from langchain.agents import Tool, initialize_agent
from langchain.agents.agent_types import AgentType
from langchain_core.prompts import PromptTemplate
from langchain_core.tools import tool
from langchain_groq import ChatGroq
from langchain.chains import LLMChain
from langchain.memory import ConversationBufferMemory
from groq import Groq
from dotenv import load_dotenv

load_dotenv()

os.environ["GROQ_API_KEY"] = os.getenv('GROQ_API_KEY')


llm = ChatGroq(model="llama-3.3-70b-versatile", max_tokens=1000, temperature=0)

# ------------------------------
# Load Context Files
# ------------------------------

# Load JSON context for Knowledge Graph Overview
# Path to your JSON file
file_path = 'knowledge_graph.json'

# Read and store JSON content as a string
with open(file_path, 'r', encoding='utf-8') as file:
    json_data = json.load(file)
    json_string = json.dumps(json_data)


file_path = 'cleaned.md'

# Read and store JSON content as a string
with open(file_path, 'r', encoding='utf-8') as file:
    md_string = file.read()   

# Load Markdown context for Test Report Data
with open("cleaned.md", "r") as f:
    test_report_data = f.read()

# ------------------------------
# Define Tool: Knowledge Graph Overview
# ------------------------------
@tool("Knowledge Graph Overview")
def knowledge_graph_tool(query: str) -> str:
    """Use this tool to answer questions related to the medical knowledge graph."""
    
    template = """
        You are an expert AI analyst working with a structured knowledge graph represented in JSON format. 
        Your task is to extract concise, accurate answers to user questions based on the relationships and entities in the graph.

        Given the following JSON knowledge graph:
        
        {json_string}

        User's question: {question}

        Please provide a clear and concise answer:
        """
    prompt = PromptTemplate(
        input_variables=["json_string", "question"],
        template=template,
    )
    qa_chain = prompt | llm
    return qa_chain.invoke({"json_string": json_string, "question": query})



# ------------------------------
# Define Tool: Test Report Data
# ------------------------------
@tool("Test Report Data")
def test_report_tool(query: str) -> str:
    """Use this tool to answer questions about the patient's medical test report."""
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
    prompt = PromptTemplate(
        input_variables=["md_string", "question"],
        template=template,
    )
    qa_chain = prompt | llm
    return qa_chain.invoke({"md_string": md_string, "question": query})

# ------------------------------
# Define Tool: Generic Web Search (Doctor Persona)
# ------------------------------
@tool("Generic Web Search")
def web_search_tool(query: str) -> str:
    """Use this tool for general web search-like queries in the medical domain. The assistant plays the role of an experienced doctor."""
    template = """
        You are a highly experienced medical professional with over 10 years of clinical expertise in diagnostics, internal medicine, and interpreting patient symptoms and test results.

        Your task is to provide a **concise, medically accurate response** to the following query. Use your clinical judgment to highlight key insights, possible causes, and recommended next steps. Avoid unnecessary jargon, but maintain a professional and authoritative tone.

        Respond as if you are advising a fellow clinician or a well-informed patient. Focus on clarity, precision, and actionable guidance.

        Here is the medical query:
        {question}

        Please provide a clear and concise answer:
        """
    prompt = PromptTemplate(
        input_variables=["question"],
        template=template,
    )
    qa_chain = prompt | llm
    return qa_chain.invoke({"question": query})


# ------------------------------
# Setup Groq LLM
# ------------------------------
llm = ChatGroq(model="llama-3.3-70b-versatile", max_tokens=1000, temperature=0)
#llm = ChatGroq(model="Llama Guard 4 12B", max_tokens=1000, temperature=0) # "Llama-3.1-8B-Instant"
# ------------------------------
# Create Tools List
# ------------------------------
tools = [knowledge_graph_tool, test_report_tool, web_search_tool]

# ------------------------------
# Create Agent
# ------------------------------
memory = ConversationBufferMemory(memory_key="chat_history", return_messages=True)

agent_executor = initialize_agent(
    tools=tools,
    llm=llm,
    agent=AgentType.ZERO_SHOT_REACT_DESCRIPTION,
    verbose=False,
    memory=memory,
)

# ------------------------------
# Main Function to Interact
# ------------------------------
def main():
    print("🧠 Medical Assistant Agent")
    print("Type 'exit' to quit.")
    while True:
        query = input("\nUser: ")
        if query.lower() == "exit":
            break
        response = agent_executor.invoke(query)
        print(f"\n🤖 Agent: {response['output']}")

if __name__ == "__main__":
    main()
