from langchain_openai import ChatOpenAI
from groq import Groq
from langchain_groq import ChatGroq
from langchain_core.runnables.history import RunnableWithMessageHistory
#from langchain.memory import ChatMessageHistory
from langchain_community.chat_message_histories import ChatMessageHistory

from langchain_experimental.agents.agent_toolkits import create_pandas_dataframe_agent
from langchain_experimental.agents.agent_toolkits.csv.base import create_csv_agent

from langchain_experimental.tools.python.tool import PythonREPLTool
from langchain_experimental.agents.agent_toolkits.python.base import create_python_agent

from langchain.agents import AgentType
import pandas as pd
import numpy as np
from datetime import datetime, timedelta



from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder
from langchain.prompts import PromptTemplate
import os
from dotenv import load_dotenv

load_dotenv()

os.environ["GROQ_API_KEY"] = os.getenv('GROQ_API_KEY')

llm = ChatGroq(model="llama-3.3-70b-versatile", max_tokens=1000, temperature=0)


# 2. Specify the CSV file path
# Create a dummy CSV file for demonstration
with open("sample.csv", "w") as f:
    f.write("Name,Age,City\n")
    f.write("Alice,30,New York\n")
    f.write("Bob,24,London\n")
    f.write("Charlie,35,Paris\n")

csv_file = "sample.csv"

# 3. Create the CSV agent
agent = create_csv_agent(
    llm,
    csv_file,
    verbose=True, # Set to True to see the agent's thought process
    # Add this parameter to explicitly allow dangerous code execution
    allow_dangerous_code=True
)

# 4. Run a query
query = "What is the average age of the people in the CSV whose name is more than 4 charaters?"
response = agent.invoke(query)

# 5. Print the response
print(f"\nQuery: {query}")
print(f"Response: {response['output']}")

# Clean up the dummy CSV file
os.remove("sample.csv")

python_repl_tool = PythonREPLTool()

# Create the Python agent
agent_executor = create_python_agent(
    llm=llm,
    tool=python_repl_tool,
    verbose=True,  # Set to True to see the agent's thought process
    allow_dangerous_code=True # Acknowledge the security implications of running arbitrary code
)

# Run the agent with a query
query = "What is the result of 15 * 23?"
response = agent_executor.invoke({"input": query})

print(f"Agent's response: {response['output']}")

# Example with a more complex operation
query_complex = "Calculate the square root of 625 and then add 10 to the result."
response_complex = agent_executor.invoke({"input": query_complex})

print(f"Agent's response (complex): {response_complex['output']}")