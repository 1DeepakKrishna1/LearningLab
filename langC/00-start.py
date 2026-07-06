import os
from dotenv import load_dotenv

from groq import Groq



# Load environment variables from a .env file
load_dotenv()

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)

chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": "Explain the importance of fast language models",
        }
    ],
    model="llama-3.3-70b-versatile",
)

# print(chat_completion.choices[0].message.content)

# Example:
from pydantic import Field
from pydantic import BaseModel
from typing import List, Optional, Any


class GenerateQuestionsRequest(BaseModel):
    statement: str
    categories: List[str] = Field(default_factory=list)
    n: int = 3

 
 
CATEGORIES = [
  'Go/NoGo',
  'Clarification',
  'Assumption',
  'Critical',
  'Cause',
  'Effect',
  'Action',
]

req = GenerateQuestionsRequest(
    statement="I want to learn Object-Oriented Programming?",
    categories=CATEGORIES,
    n=10
)

prompt = f"You are a Precision Q+A Generator.\nUser statement: \"{req.statement}\"\nSelected categories: {req.categories}\nGenerate exactly {req.n} questions.\nFollow Precision Question Framework categories.\nEnsure coverage of chosen categories.\n Return only Json that contain the list of question and categoryName. \nReturn JSON: [{{ \"question\": \"...\", \"category\": \"...\" }}]"

chat_completion = client.chat.completions.create(
    messages=[
        {
            "role": "user",
            "content": prompt,
        }
    ],
    model="llama-3.3-70b-versatile",
)

print(chat_completion.choices[0].message.content)