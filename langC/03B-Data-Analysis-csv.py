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




csv_file = "lab_report_data.csv"

# 3. Create the CSV agent
agent = create_csv_agent(
    llm,
    csv_file,
    verbose=True, # Set to True to see the agent's thought process
    # Add this parameter to explicitly allow dangerous code execution
    allow_dangerous_code=True
)

# 4. Run a query
query = "What is UIBCvalue?"
response = agent.invoke(query)

# 5. Print the response
print(f"\nQuery: {query}")
print(f"Response: {response['output']}")