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


load_dotenv()

os.environ["GROQ_API_KEY"] = os.getenv('GROQ_API_KEY')


llm = ChatGroq(model="llama-3.3-70b-versatile", max_tokens=1000, temperature=0)

# Path to your JSON file
file_path = 'knowledge_graph.json'

# Read and store JSON content as a string
with open(file_path, 'r', encoding='utf-8') as file:
    json_data = json.load(file)
    json_string = json.dumps(json_data)






template = """
You are an expert AI analyst working with a structured knowledge graph represented in JSON format. 
Your task is to extract concise, accurate answers to user questions based on the relationships and entities in the graph.

Given the following JSON knowledge graph:
 
{json_string}

User's question: {question}

Please provide a clear and concise answer:
"""

#filled_prompt = template.format(json_string=json.dumps(json_string, indent=2))


prompt = PromptTemplate(template=template, input_variables=["question"])

print(prompt.format( json_string=json_string, question="What is the name of the patient?"))

print("*****************************************************************")

qa_chain = prompt | llm

def get_answer(question, json_string=json_string):
    """
    Get an answer to the given question using the QA chain.
    """
    input_variables = {"question": question, "json_string": json_string}
    response = qa_chain.invoke(input_variables).content
    return response

question = "What is the name of the patient?"
answer = get_answer(question)
print(f"Question: {question}")
print(f"Answer: {answer}")

user_question = input("Enter your question: ")
user_answer = get_answer(user_question)
print(f"Answer: {user_answer}")