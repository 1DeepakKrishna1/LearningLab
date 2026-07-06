import os
from dotenv import load_dotenv

from groq import Groq



# Load environment variables from a .env file
load_dotenv()

client = Groq(
    api_key=os.environ.get("GROQ_API_KEY"),
)


# Example 1:
from pydantic import Field
from pydantic import BaseModel
from typing import List, Optional, Any
import json


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
    statement="I want to learn swimming?",
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
print("\n---XXX---\n")


# Example 2:

class EvaluateAnswersRequest(BaseModel):
    statement: str
    qa: List[dict]


class EvaluationResult(BaseModel):
    question: str
    answer: str
    rating: int
    explanation: str
    next_questions: List[str]


req = EvaluateAnswersRequest(
    statement="I want to learn Object-Oriented Programming?",
    qa=[
        {
            "question": "What is OOP?",
            "answer": "OOP stands for Object-Oriented Programming."
        },
        {
            "question": "What are the main principles of OOP?",
            "answer": "The main principles of OOP are encapsulation, inheritance, and polymorphism."
        }
    ]
)

for a in req.qa:
        q = a.get('question', '')
        ans = a.get('answer', '')
        prompt = f"You are a Precision Q+A Answer Evaluator.\nUser statement: \"{req.statement}\"\nQuestion asked: \"{q}\"\nUser answer: \"{ans}\"\nEvaluate answer using Precision Answer Framework.\nReturn:\n- Rating (1-10)\n- Explanation of rating\n- 4 Next-Level Precision Questions for deeper exploration for the answer given for the question asked in context of the given statement.\nFollow Precision Question Framework categories.\nReturn only Json that contain rating, explanation and the list of next_questions. {CATEGORIES}\nReturn JSON: [{{ \"rating\": X, \"explanation\": \"...\", \"next_questions\": [...] }}]"
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



prompt = f"You are a Precision Q+A Answer Evaluator.\nUser statement: \"{req.statement}\"\nQuestion and their respective Answers are: {json.dumps(req.qa)}\nEvaluate answers using Precision Answer Framework.\nReturn:\n- Rating (1-10)\n- Explanation of rating\n- 4 Next-Level Precision Questions for deeper exploration for the answer given for the question asked in context of the given statement.\nFollow Precision Question Framework categories.\nReturn only Json that contain question, answer, rating, explanation and the list of next_questions. {CATEGORIES}\nReturn JSON: [{{ \"question\": \"...\", \"answer\": \"...\",\"rating\": X, \"explanation\": \"...\", \"next_questions\": [...] }}]"

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


# Example 3:
class FinalEvaluationRequest(BaseModel):
    statement: str
    qa: List[dict]


class FinalAnswerResult(BaseModel):
    statement: str
    readiness_score: int
    recommendations: List[str]
    next_steps: List[str]

class FinalAnswerResult_1(BaseModel):
    question: str
    answer: str
    rating: int
    explanation: str    

req = FinalEvaluationRequest(
    statement="I want to learn Object-Oriented Programming?",
    qa=[
        {
            "question": "What is OOP?",
            "answer": "OOP stands for Object-Oriented Programming."
        },
        {
            "question": "What are the main principles of OOP?",
            "answer": "The main principles of OOP are encapsulation, inheritance, and polymorphism."
        }
    ]
)

prompt = f"You are a Precision Q+A Evaluator AI Assistant.\nStatement: \"{req.statement}\"\n Question and Answers: {json.dumps(req.qa)}\n Create the context from it and provide user statement, current readiness score (1-100), SWOT recommendations and next steps for the statement: {req.statement}.\nReturn only Json that contain statement, readiness_score, list of recommendations, list of next steps\nReturn JSON: [{{ \"statement\":\"...\",  \"readiness_score\": X, \"recommendations\": [...], \"next_steps\": [...] }}]"

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
print("\n---parsed json---\n")

json_string = chat_completion.choices[0].message.content
data_list = json.loads(json_string)
results = [FinalAnswerResult.model_validate_json(json.dumps(item)) for item in data_list]

# Print each object
for result in results:
    print(result)




