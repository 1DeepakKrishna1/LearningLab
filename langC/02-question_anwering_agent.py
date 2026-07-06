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

load_dotenv()

os.environ["GROQ_API_KEY"] = os.getenv('GROQ_API_KEY')


llm = ChatGroq(model="llama-3.3-70b-versatile", max_tokens=1000, temperature=0)

template = """
You are a helpful AI assistant. Your task is to answer the user's question to the best of your ability.

User's question: {question}

Please provide a clear and concise answer:
"""

prompt = PromptTemplate(template=template, input_variables=["question"])

qa_chain = prompt | llm

def get_answer(question):
    """
    Get an answer to the given question using the QA chain.
    """
    input_variables = {"question": question}
    response = qa_chain.invoke(input_variables).content
    return response

question = "What is the capital of France?"
answer = get_answer(question)
print(f"Question: {question}")
print(f"Answer: {answer}")

user_question = input("Enter your question: ")
user_answer = get_answer(user_question)
print(f"Answer: {user_answer}")