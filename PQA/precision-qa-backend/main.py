from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
import os
import json
from typing import Callable, Optional, Any
from dotenv import load_dotenv

load_dotenv()
from pydantic import BaseModel
from typing import List, Optional, Any
import httpx

# Import the agentic chat handler
from Agentic_Chat import handle_subject_request, update_content_variables

app = FastAPI(title="Precision QA Backend")

# ------------------------------
# Content Loading Function
# ------------------------------
def load_content_from_folder(folder_path: str = 'C:/allCode/code_DK/Data/foo/'):
    """
    Load content from input folder location including:
    - json_string from knowledge_graph.json
    - test_report_data from original.pdf and cleaned.md files

    Args:
        folder_path (str): Path to the folder containing the files

    Returns:
        dict: Dictionary containing loaded content
    """
    try:
        content = {
            "json_string": None,
            "test_report_data": None,
            "md_string": None,
            "status": "success",
            "error": None
        }

        # Load JSON content for Knowledge Graph Overview
        json_file_path = os.path.join(folder_path, 'knowledge_graph.json')
        if os.path.exists(json_file_path):
            with open(json_file_path, 'r', encoding='utf-8') as file:
                json_data = json.load(file)
                content["json_string"] = json.dumps(json_data)
        else:
            print(f"Warning: knowledge_graph.json not found at {json_file_path}")

        # Load Markdown content from cleaned.md
        md_file_path = os.path.join(folder_path, 'cleaned.md')
        if os.path.exists(md_file_path):
            with open(md_file_path, 'r', encoding='utf-8') as file:
                content["md_string"] = file.read()
                content["test_report_data"] = content["md_string"]  # Same content for both
        else:
            print(f"Warning: cleaned.md not found at {md_file_path}")

        # Check for original.pdf (note: this would require PDF parsing library)
        pdf_file_path = os.path.join(folder_path, 'original.pdf')
        if os.path.exists(pdf_file_path):
            print(f"Note: original.pdf found at {pdf_file_path} but PDF parsing not implemented")
            # If you want to parse PDF, you would need to add a PDF parsing library
            # For now, we'll use the cleaned.md content as the test_report_data

        return content

    except Exception as e:
        return {
            "json_string": None,
            "test_report_data": None,
            "md_string": None,
            "status": "error",
            "error": str(e)
        }

def resolve_folder(input_string, base_path):
    try:
        # Split the string by "@@" and take the first part
        folder_name = input_string.split("@@")[0].lower().strip()

        # Get list of folders in the given base path        
        folders = [f for f in os.listdir(base_path) if os.path.isdir(os.path.join(base_path, f))]

        # Match folder name or default to "foo"
        #matched_folder = folder_name if folder_name in folders else "foo"
        matched_folder = next((f for f in folders if folder_name in f.lower()), "foo")

        return os.path.join(base_path, matched_folder)
    except FileNotFoundError as e:
        print(f"INPUTs '{input_string}' AND  '{base_path}' have issues.", str(e ))
        return os.path.join(base_path, "foo")


# Allow local frontend dev server to call this API
# Configure CORS from environment variable ALLOWED_ORIGINS (comma-separated). Defaults to localhost:3100
allowed = os.getenv('ALLOWED_ORIGINS')
if allowed:
    allow_origins = [o.strip() for o in allowed.split(',') if o.strip()]
else:
    allow_origins = ["http://localhost:3100", "http://127.0.0.1:3100", "http://localhost:3000", "http://127.0.0.1:3000"]

print("ALLOWED_ORIGINS:", allow_origins)


app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
print( "ALLOWED_ORIGINS: *")

# LLM provider abstraction: if GROQ_API_KEY and GROQ_ENDPOINT are set, use Groq.
# Otherwise use deterministic fallback functions.
GROQ_API_KEY = os.getenv('GROQ_API_KEY')
GROQ_ENDPOINT = os.getenv('GROQ_ENDPOINT')

async def groq_call(prompt: str) -> Optional[str]:
    """Call Groq provider. Try SDK (ChatGroq) if available and configured; otherwise use raw HTTP POST.
    Returns the provider's text response or None on error.
    """
    if not GROQ_API_KEY and not GROQ_ENDPOINT:
        return None

    # Try SDK first (ChatGroq) if available
    try:
        # Use the langchain_groq ChatGroq SDK when available (per your snippet)
        from langchain_groq import ChatGroq
        import asyncio

        model = os.getenv('GROQ_MODEL', 'llama-3.3-70b-versatile')
        max_tokens = int(os.getenv('GROQ_MAX_TOKENS', '1000'))
        temperature = float(os.getenv('GROQ_TEMPERATURE', '0'))

        llm = ChatGroq(model=model, max_tokens=max_tokens, temperature=temperature)

        # langchain-style LLMs are synchronous; run in thread to avoid blocking the event loop
        try:
            resp = await asyncio.to_thread(lambda: llm(prompt))
        except TypeError:
            # If llm is callable with different signature
            resp = await asyncio.to_thread(lambda: llm.generate(prompt) if hasattr(llm, 'generate') else llm(prompt))

        # resp may be a string or an object; try to return a string or JSON
        if isinstance(resp, str):
            return resp
        if hasattr(resp, 'text'):
            return resp.text
        if isinstance(resp, dict):
            return json.dumps(resp)
    except Exception as e:
        # SDK not available or failed; log and fallback to HTTP
        print('ChatGroq SDK call failed or not available:', e)
        pass

    # HTTP POST fallback
    if not GROQ_ENDPOINT:
        return None
    try:
        headers = {
            'Content-Type': 'application/json',
            'Authorization': f'Bearer {GROQ_API_KEY}'
        }
        payload = {
            'prompt': prompt,
            'max_tokens': int(os.getenv('GROQ_MAX_TOKENS', '1000')),
            'temperature': float(os.getenv('GROQ_TEMPERATURE', '0')),
        }
        async with httpx.AsyncClient() as client:
            r = await client.post(GROQ_ENDPOINT, json=payload, headers=headers, timeout=60.0)
            r.raise_for_status()
            return r.text
    except Exception as e:
        print('Groq HTTP call failed:', e)
        return None


async def run_or_fallback(prompt: str, fallback: Callable[[str], Any]):
    """Try LLM provider; if not available or fails, call fallback(prompt) which returns structured data."""
    res = await groq_call(prompt)
    if res is None:
        # provider not configured or failed, use fallback
        return fallback(prompt)
    # If provider returned JSON text, try parsing; otherwise return raw
    try:
        return json.loads(res)
    except Exception:
        return res


class GenerateRequest(BaseModel):
    statement: str
    categories: List[str]
    count: int


class QAItem(BaseModel):
    question: str


class SubmitRequest(BaseModel):
    statement: str
    categories: List[str]
    qa: List[dict]
    stage: Optional[str] = 'first'


class ContextData(BaseModel):
    starting_point: str = ''
    intent: str = ''
    supporting_data: str = ''
    constraints: str = ''
    persona: str = ''


# Context storage file path
CONTEXT_FILE = "context.json"

@app.get("/")
async def read_root():
    return {"message": "Precision QA backend is running."}


@app.post('/store-context')
async def store_context(context: ContextData):
    """Store context data to a JSON file"""
    try:
        context_dict = context.model_dump()
        with open(CONTEXT_FILE, 'w') as f:
            json.dump(context_dict, f, indent=2)
        return {"message": "Context stored successfully"}
    except Exception as e:
        return {"error": f"Failed to store context: {str(e)}"}


@app.get('/load-context')
async def load_context(context: Optional[str] = None):
    """
    Load context data from JSON file

    Args:
        context (Optional[str]): Optional parameter to specify a custom context file name
                                If provided, will look for a file with this name
                                If not provided, uses the default context.json file
    """
    try:
        # Determine which file to load
        if context:
            # Use custom context file name
            context_file_path = f"{context}.json" if not context.endswith('.json') else context
            # Ensure the file is in the same directory as the default context file
            context_file_path = os.path.join(os.path.dirname(CONTEXT_FILE), context_file_path)
        else:
            # Use default context file
            context_file_path = CONTEXT_FILE

        if os.path.exists(context_file_path):
            with open(context_file_path, 'r') as f:
                context_data = json.load(f)
            return {
                **context_data,
                "loaded_from": context_file_path,
                "custom_context": context is not None
            }
        else:
            # Return empty context if file doesn't exist
            empty_context = {
                "starting_point": "",
                "intent": "",
                "supporting_data": "",
                "constraints": "",
                "persona": "",
                "loaded_from": context_file_path if context else "default",
                "custom_context": context is not None,
                "file_exists": False
            }

            if context:
                empty_context["message"] = f"Custom context file '{context_file_path}' not found, returning empty context"

            return empty_context

    except Exception as e:
        return {
            "starting_point": "",
            "intent": "",
            "supporting_data": "",
            "constraints": "",
            "persona": "",
            "error": f"Failed to load context: {str(e)}",
            "loaded_from": context_file_path if 'context_file_path' in locals() else "unknown",
            "custom_context": context is not None
        }


@app.get('/set-context')
async def set_context(context: str):
    """
    Set the context by copying content from a specified file to context.json

    Args:
        context (str): Required parameter specifying the source context file name
                      Will look for a file with this name and copy its content to context.json
    """
    try:
        print("Set context:", context)
        # Validate that context parameter is provided
        if not context or not context.strip():
            return {
                "error": "Context parameter is required",
                "status": "error",
                "message": "Please provide a context filename parameter"
            }

        # Prepare source file path
        source_file = f"{context.strip()}.json" if not context.strip().endswith('.json') else context.strip()
        source_file_path = os.path.join(os.path.dirname(CONTEXT_FILE), source_file)

        # Check if source file exists
        if not os.path.exists(source_file_path):
            return {
                "error": f"Source context file '{source_file}' not found",
                "status": "error",
                "source_file": source_file_path,
                "message": f"The file '{source_file}' does not exist in the context directory"
            }

        # Read content from source file
        with open(source_file_path, 'r', encoding='utf-8') as f:
            source_content = json.load(f)

        # Write content to context.json (destination)
        with open(CONTEXT_FILE, 'w', encoding='utf-8') as f:
            json.dump(source_content, f, indent=2)

        return {
            "message": f"Context successfully set from '{source_file}'",
            "status": "success",
            "source_file": source_file_path,
            "destination_file": CONTEXT_FILE,
            "context_data": source_content
        }

    except json.JSONDecodeError as e:
        return {
            "error": f"Invalid JSON in source file '{source_file}': {str(e)}",
            "status": "error",
            "source_file": source_file_path if 'source_file_path' in locals() else "unknown"
        }
    except Exception as e:
        return {
            "error": f"Failed to set context: {str(e)}",
            "status": "error",
            "source_file": source_file_path if 'source_file_path' in locals() else "unknown",
            "destination_file": CONTEXT_FILE
        }


@app.post('/generate')
async def generate(req: GenerateRequest):
    # Simple deterministic question generator: combine category + index
    cats = req.categories or ['General']
    questions = []
    for i in range(req.count):
        cat = cats[i % len(cats)]
        q = f"({cat}) Please evaluate part #{i+1} of the statement: '{req.statement[:80]}'"
        questions.append(q)
    return {"questions": questions}


@app.post('/submit')
async def submit(req: SubmitRequest):
    # Simple behavior: if stage == 'first' return some next-level questions, otherwise return final summary
    if req.stage == 'first':
        # produce next-level questions for the first stage
        next_q = [f"Follow-up for: {a.get('question', 'q')}" for a in req.qa][:max(1, len(req.qa)//2)]
        return {"next_questions": next_q}

    # final summary: assign ratings and explanations
    items = []
    total = 0
    for idx, a in enumerate(req.qa):
        answer_text = a.get('answer', '')
        # rating heuristic: length-based (deterministic)
        rating = min(10, max(1, len(answer_text.strip()) // 10 + 1))
        total += rating
        items.append({
            'question': a.get('question', f'Q{idx+1}'),
            'answer': answer_text,
            'rating': rating,
            'explanation': f"Auto-explanation: answer length={len(answer_text)} chars; rating={rating}.",
        })

    overall = round(total / (len(items) or 1), 2)
    recs = "Consider clarifying assumptions, adding missing details, and re-evaluating critical items." if overall < 7 else "You have a reasonable readiness; validate action items and monitor." 

    return {
        'summary': {
            'items': items,
            'overall_readiness': overall,
            'recommendations': recs,
        }
    }


# ---------------------------------------------------------------------------
# New endpoints matching user spec
# 1) /generate-questions
# 2) /evaluate-answers
# 3) /final-evaluation
# These endpoints return JSON in the formats described in the prompt attachments.
# Deterministic placeholder logic is used so the frontend can be tested without
# an LLM integration. Replace the placeholder logic with real LLM calls as needed.
# ---------------------------------------------------------------------------

from pydantic import Field
from fastapi import Request


class GenerateQuestionsRequest(BaseModel):
    statement: str
    categories: List[str] = Field(default_factory=list)
    n: int = 3


class GeneratedQuestion(BaseModel):
    question: str
    category: str

from groq import Groq
import json


@app.post('/generate-questions')
async def generate_questions(req: GenerateQuestionsRequest):
    # Build LLM prompt according to provided template
    prompt = f"You are a Precision Q+A Generator.\nUser statement: \"{req.statement}\"\nSelected categories: {req.categories}\nGenerate exactly {req.n} questions.\nFollow Precision Question Framework categories.\nEnsure coverage of chosen categories.\n Return only Json that contain the list of QuestionId, Question and categoryName. \nReturn JSON: [{{ \"question\": \"...\", \"category\": \"...\" }}]"
    print ("Prompt:", prompt)
    client = Groq(
        api_key=os.environ.get("GROQ_API_KEY"),
    )
    
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="llama-3.3-70b-versatile",
    )

    print("Chat completion:", chat_completion)
    print("Content:", chat_completion.choices[0].message.content)

    return {"questions": json.loads(chat_completion.choices[0].message.content)}

@app.post('/generate-questions_1')
async def generate_questions_1(req: GenerateQuestionsRequest):
    # Build LLM prompt according to provided template
    prompt = f"You are a Precision Q+A Generator.\nUser statement: \"{req.statement}\"\nSelected categories: {req.categories}\nGenerate exactly {req.n} questions.\nFollow Precision Question Framework categories.\nEnsure coverage of chosen categories.\nReturn JSON: [{{ \"question\": \"...\", \"category\": \"...\" }}]"

    async def fallback(p: str):
        cats = req.categories or ['General']
        qlist: List[GeneratedQuestion] = []
        for i in range(req.n):
            cat = cats[i % len(cats)]
            qtxt = f"({cat}) In relation to: '{req.statement[:120]}', what is item #{i+1}?"
            qlist.append(GeneratedQuestion(question=qtxt, category=cat))
        return {"questions": [q.dict() for q in qlist]}

    result = await run_or_fallback(prompt, fallback)
    # If LLM returned a dict with 'questions', return it; else try to coerce
    if isinstance(result, dict) and 'questions' in result:
        return result
    # If result is a list of objects
    if isinstance(result, list):
        return {"questions": result}
    # Fallback: return deterministic
    return await fallback(prompt)


class EvaluateAnswersRequest(BaseModel):
    statement: str
    qa: List[dict]


class EvaluationResult(BaseModel):
    question: str
    answer: str
    rating: int
    explanation: str
    next_questions: List[str]


@app.post('/evaluate-answers')
async def evaluate_answers(req: EvaluateAnswersRequest):
    # Build LLM prompt according to provided template
    CATEGORIES = [
    'Go/NoGo',
    'Clarification',
    'Assumption',
    'Critical',
    'Cause',
    'Effect',
    'Action',
    ]
    
    prompt = f"You are a Precision Q+A Answer Evaluator.\nUser statement: \"{req.statement}\"\nQuestion and their respective Answers are: {json.dumps(req.qa)}\n Evaluate answers using Precision Answer Framework.\nReturn:\n- Rating (1-10)\n- Explanation of rating\n- 4 Next-Level Precision Questions for deeper exploration for the answer given for the question asked in context of the given statement.\nFollow Precision Question Framework categories.\nReturn only Json that contain question, answer, rating, explanation and the list of next_questions. {CATEGORIES}\nReturn JSON: [{{ \"question\": \"...\", \"answer\": \"...\",\"rating\": X, \"explanation\": \"...\", \"next_questions\": [...] }}]"
    print ("Prompt:", prompt)
    client = Groq(
        api_key=os.environ.get("GROQ_API_KEY"),
    )
    
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="llama-3.3-70b-versatile",
    )

    print("Chat completion:", chat_completion)
    print("Content:", chat_completion.choices[0].message.content)

    return {"evaluations": json.loads(chat_completion.choices[0].message.content)}


async def evaluate_answers_1(req: EvaluateAnswersRequest):
    # Create a prompt per answer and attempt LLM evaluation; if LLM not available, fallback
    evaluations = []

    async def fallback_single(q_txt, ans_txt):
        rating = min(10, max(1, len(ans_txt.strip()) // 12 + (0 if ans_txt.strip() == '' else 1)))
        explanation = f"Auto-eval: answer length={len(ans_txt)} chars; rating={rating}. Look for specificity and evidence to increase rating."
        next_qs = [
            f"Please clarify the key assumption behind: '{q_txt}'",
            f"What evidence supports your answer to: '{q_txt}'?",
            f"If this is incorrect, what is an alternative explanation for: '{q_txt}'?",
            f"What immediate action would you recommend based on your answer to: '{q_txt}'?",
        ]
        return {"question": q_txt, "answer": ans_txt, "rating": rating, "explanation": explanation, "next_questions": next_qs}

    for a in req.qa:
        q = a.get('question', '')
        ans = a.get('answer', '')
        prompt = f"You are a Precision Q+A Answer Evaluator.\nUser statement: \"{req.statement}\"\nUser answer: \"{ans}\"\nEvaluate answer using Precision Answer Framework.\nReturn:\n- Rating (1-10)\n- Explanation of rating\n- 4 Next-Level Precision Questions for deeper exploration\nFormat JSON: {{ \"rating\": X, \"explanation\": \"...\", \"next_questions\": [...] }}"
        # Try provider
        out = await run_or_fallback(prompt, lambda p, q=q, ans=ans: fallback_single(q, ans))
        # If provider returned JSON with rating etc., incorporate it
        if isinstance(out, dict) and 'rating' in out:
            evaluations.append(out)
        else:
            # If provider returned a list or text, attempt to coerce, else use fallback
            try:
                parsed = json.loads(out) if isinstance(out, str) else out
                if isinstance(parsed, dict) and 'rating' in parsed:
                    evaluations.append(parsed)
                else:
                    evaluations.append(await fallback_single(q, ans))
            except Exception:
                evaluations.append(await fallback_single(q, ans))

    return {"evaluations": evaluations}


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


@app.post('/final-evaluation')
async def final_evaluation(req: FinalEvaluationRequest):
     # Build LLM prompt according to provided template
    prompt = f"You are a Precision Q+A Evaluator AI Assistant.\nStatement: \"{req.statement}\"\n Question and Answers: {json.dumps(req.qa)}\n Create the context from it and provide user statement, current readiness score (1-100), SWOT recommendations and next steps for the statement: {req.statement}.\nReturn only Json that contain statement, readiness_score, list of recommendations, list of next steps\nReturn JSON: [{{ \"statement\":\"...\",  \"readiness_score\": X, \"recommendations\": [...], \"next_steps\": [...] }}]"
    print ("Prompt:", prompt)
    client = Groq(
        api_key=os.environ.get("GROQ_API_KEY"),
    )
    
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="llama-3.3-70b-versatile",
    )

    return {"FinalResult": json.loads(chat_completion.choices[0].message.content)}


async def final_evaluation_1(req: FinalEvaluationRequest):
    # Try to use LLM to evaluate all next-level answers together; fallback to deterministic
    prompt = f"You are a Precision Q+A Evaluator.\nStatement: \"{req.statement}\"\nAnswers: {json.dumps(req.qa)}\nEvaluate each answer using Precision Answer Framework.\nReturn for each:\n- Rating (1-10)\n- Explanation\nThen calculate overall Readiness Score (0-100).\nFinally, recommend Next Steps to improve weak areas.\nFormat JSON:\n{{\n  \"answers\": [ {{ \"question\": \"...\", \"answer\": \"...\", \"rating\": X, \"explanation\": \"...\" }} ],\n  \"readiness_score\": X,\n  \"recommendations\": [...]\n}}"

    async def fallback_all(p: str):
        items = []
        total = 0
        for a in req.qa:
            q = a.get('question', '')
            ans = a.get('answer', '')
            rating = min(10, max(1, len(ans.strip()) // 10 + (0 if ans.strip() == '' else 1)))
            explanation = f"Final auto-eval: length={len(ans)}; rating={rating}. Consider adding evidence and clearer actions."
            items.append({"question": q, "answer": ans, "rating": rating, "explanation": explanation})
            total += rating

        avg_rating = total / (len(items) or 1)
        readiness_score = int(round(avg_rating * 10))
        recs = []
        weak = [it for it in items if it['rating'] < 7]
        if weak:
            recs.append(f"{len(weak)} answers scored below 7. Focus on adding evidence and clarifying assumptions for those items.")
            recs.append("Run targeted validations for critical assumptions and assign owners for action items.")
        else:
            recs.append("Answers appear strong; validate implementation plans and monitor progress.")

        return {"answers": items, "readiness_score": readiness_score, "recommendations": recs}

    result = await run_or_fallback(prompt, fallback_all)
    # Coerce to proper JSON dict
    if isinstance(result, dict) and 'answers' in result:
        return result
    try:
        parsed = json.loads(result) if isinstance(result, str) else result
        if isinstance(parsed, dict) and 'answers' in parsed:
            return parsed
    except Exception:
        pass
    return await fallback_all(prompt)


class CreatePlanRequest(BaseModel):
    statement: str
    recommendations: List[str] = Field(default_factory=list)
    next_steps: List[str] = Field(default_factory=list)


class PromptRequest(BaseModel):
    prompt: str


@app.post('/GetPromptResponse')
async def get_prompt_response(req: PromptRequest):
    """
    Takes a prompt as input and returns an LLM response.
    """
    try:
        client = Groq(
            api_key=os.environ.get("GROQ_API_KEY"),
        )

        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": req.prompt,
                }
            ],
            model="llama-3.3-70b-versatile",
            max_tokens=1000,
            temperature=0.7,
        )

        response_text = chat_completion.choices[0].message.content
        return {"response": response_text}

    except Exception as e:
        print(f"Error in GetPromptResponse: {e}")
        # Fallback response if LLM fails
        return {"response": "I apologize, but I'm unable to process your request at the moment. Please try again later."}


@app.post('/create-plan')
async def create_plan(req: Request):
    body = await req.json()
    print("Create plan request body:", body)
    # tolerate different field names and types
    statement = body.get('statement') or body.get('statementText') or body.get('user_statement') or ''
    recommendations = body.get('recommendations') or body.get('recs') or []
    next_steps = body.get('next_steps') or body.get('nextSteps') or body.get('next') or []
    # accept QA payload under multiple keys for compatibility
    qa = body.get('qa') or body.get('qaList') or body.get('qalist') or []

     # Build LLM prompt according to provided template
    prompt = f"You are an experienced Precision Q+A Trainer and AI Assistant.\n Get the context from Question and Answers: {qa}\n Recommendations : {recommendations} , next action steps: {next_steps}.\nExecute the Task: How to \"{statement}\" Format the response into a well-structured professional guide in md format.\n"
    print ("Prompt:", prompt)
    client = Groq(
        api_key=os.environ.get("GROQ_API_KEY"),
    )
    
    chat_completion = client.chat.completions.create(
        messages=[
            {
                "role": "user",
                "content": prompt,
            }
        ],
        model="llama-3.3-70b-versatile",
    ) 
    print("Content:", chat_completion.choices[0].message.content)  
    return chat_completion.choices[0].message.content


async def create_plan_1(request: Request):
    body = await request.json()
    print("Create plan request body:", body)
    # tolerate different field names and types
    statement = body.get('statement') or body.get('statementText') or body.get('user_statement') or ''
    recommendations = body.get('recommendations') or body.get('recs') or []
    next_steps = body.get('next_steps') or body.get('nextSteps') or body.get('next') or []
    # accept QA payload under multiple keys for compatibility
    qa = body.get('qa') or body.get('qaList') or body.get('qalist') or []
    # coerce QA string to list if necessary
    if isinstance(qa, str):
        try:
            qa = json.loads(qa)
        except Exception:
            qa = [qa]
    # coerce strings to lists
    if isinstance(recommendations, str):
        recommendations = [recommendations]
    if isinstance(next_steps, str):
        next_steps = [next_steps]

    # include QA context in the prompt to help the LLM produce a plan that references the actual questions and answers
    qa_context = qa if isinstance(qa, (list, dict)) else [qa]
    try:
        qa_json = json.dumps(qa_context)
    except Exception:
        qa_json = str(qa_context)

    prompt = f"You are a planning AI assistant and consultant. Use the following Q/A context to inform the plan:\nQ/A Context: {qa_json}\nUser statement: '{statement}'\nConsider Recommendations: {recommendations}\nImmediate Next steps: {next_steps}\nProduce a clear, prioritized implementation weekly plan. Include: Overview, Objectives, SMART Tasks (with owners and due dates in ISO format placeholders), Milestones, Risks and Mitigations. Return JSON with keys: overview, objectives (list), tasks (list of {{title, description, owner, due_date}}), milestones (list), risks (list of {{risk, mitigation}})."

    async def fallback_plan(p: str):
        # deterministic simple plan
        tasks = []
        # Create tasks from next_steps when available
        for i, ns in enumerate(next_steps, start=1):
            tasks.append({
                'title': f'Task {i}: {ns[:40]}',
                'description': ns,
                'owner': 'TBD',
                'due_date': '2025-12-31',
            })

        # Also create tasks from QA context to preserve traceability
        for j, qa_item in enumerate(qa_context, start=len(tasks)+1):
            qtxt = ''
            atxt = ''
            if isinstance(qa_item, dict):
                qtxt = qa_item.get('question') or qa_item.get('q') or ''
                atxt = qa_item.get('answer') or qa_item.get('a') or ''
            else:
                # if the item is a primitive or string, place it into description
                qtxt = str(qa_item)

            if qtxt or atxt:
                tasks.append({
                    'title': f'Investigate: { (qtxt[:50] or atxt[:50]) }',
                    'description': f'Question: {qtxt}\nAnswer: {atxt}',
                    'owner': 'TBD',
                    'due_date': '2025-12-31',
                })

        milestones = [f'Milestone {i+1}: Complete task {i+1}' for i in range(len(tasks))] or ['Initial review']
        risks = []
        if len(recommendations) == 0:
            risks.append({'risk': 'Insufficient recommendations selected', 'mitigation': 'Re-run evaluation to surface more recommendations.'})
        else:
            for r in recommendations:
                risks.append({'risk': f'Risk related to recommendation: {r[:60]}', 'mitigation': 'Assign owner and track progress.'})

        plan = {
            'overview': f"Plan for: {statement}",
            'objectives': [f"Address: {r}" for r in recommendations] or ["Clarify and validate statement."],
            'tasks': tasks,
            'milestones': milestones,
            'risks': risks,
        }
        return plan

    result = await run_or_fallback(prompt, fallback_plan)
    # ensure it's serializable dict
    if isinstance(result, dict):
        return {'plan': result}
    try:
        return {'plan': json.loads(result)}
    except Exception:
        return {'plan': await fallback_plan(prompt)}

class SubjectRequest(BaseModel):
    subject: str
    body: str


@app.post("/mail/client")
async def respond_to_subject(data: SubjectRequest):
    # Example logic: parse or respond based on subject
    print("Respond to subject:", data)
    print("Subject:", data.subject)
    print("Body:", data.body)

    if (len(data.body) > 10):
        body_text = "From the Context:" + data.body
    else:
        body_text = ""

    if(body_text != "" ):
        subject_text = data.subject.replace("Aisal:", "\nTask: ")
    else:
        subject_text = data.subject.replace("Aisal:", "Explain in around 100 words what is ")

    try:
        client = Groq(
            api_key=os.environ.get("GROQ_API_KEY"),
        )

        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": body_text + subject_text,
                }
            ],
            model="llama-3.3-70b-versatile",
            max_tokens=1000,
            temperature=0.7,
        )

        response_text = chat_completion.choices[0].message.content
        return {"response": response_text}

    except Exception as e:
        print(f"Error in GetPromptResponse: {e}")
        # Fallback response if LLM fails
        return {"response": "I apologize, but I'm unable to process your request at the moment. Please try again later."}
    

@app.post("/mail/admin")
async def respond_to_subject(data: SubjectRequest):
    # Example logic: parse or respond based on subject
    print("Respond to subject:", data)
    print("Subject:", data.subject)
    print("Body:", data.body)

    body_text = data.body
    subject_text = data.subject.replace("AisalAdmin:", "")

    createPromptText = '''
        Given the following context, generate a clear, concise, and effective prompt that captures the user's intent and guides an AI assistant to respond appropriately. The generated prompt should be specific, actionable, and aligned with the original context.
        Context:
        [Insert your text here]
        Output Format:
        • 	Should begin with an action verb (e.g., "Summarize", "Explain", "Generate", "Translate", "Create", "List")
        • 	Avoid vague or open-ended phrasing
        • 	Ensure the prompt is tailored to the context provided
    '''

    if(subject_text == "Generate" ):
        execute_text = createPromptText.replace("[Insert your text here]", body_text)
    elif(subject_text == "Execute" ):
        execute_text = body_text
    else:
        raise Exception("Invalid Subject text in the mail !")


    try:
        client = Groq(
            api_key=os.environ.get("GROQ_API_KEY"),
        )

        chat_completion = client.chat.completions.create(
            messages=[
                {
                    "role": "user",
                    "content": execute_text,
                }
            ],
            model="llama-3.3-70b-versatile",
            max_tokens=1000,
            temperature=0.7,
        )

        response_text = chat_completion.choices[0].message.content
        return {"response": response_text}

    except Exception as e:
        print(f"Error in GetPromptResponse: {e}")
        # Fallback response if LLM fails
        return {"response": "I apologize, but I'm unable to process your request at the moment. Please try again later."}

@app.post("/mail/chat")
async def respond_to_subject(data: SubjectRequest):
    """
    Handle chat requests by loading content from folder and passing SubjectRequest to the agentic chat system
    """
    try:

        print("Respond to subject:", data.subject)
        base_path = 'C:/allCode/code_DK/Data/'
        data.subject = data.subject.replace("AisalChat:", "")
        folder_name = resolve_folder(data.subject, base_path)
        # Split the string by "@@" and take the first part

        if "@@" in data.subject:
            data.subject = data.subject.split("@@")[1].lower().strip()

        # Load content from input folder before processing the request
        print("Loading content from input folder...", folder_name)
        print("input:", data)
        content = load_content_from_folder(folder_name)  # deault : 'C:/allCode/code_DK/Data/foo/'

        if content["status"] == "error":
            print(f"Warning: Error loading content - {content['error']}")
            # Continue with processing even if content loading fails
        else:
            # Update the agentic chat system with the loaded content
            update_content_variables(
                new_json_string=content.get("json_string"),
                new_md_string=content.get("md_string"),
                new_test_report_data=content.get("test_report_data")
            )
            print("Content successfully loaded and updated in agentic chat system")

        # Pass the SubjectRequest to the agentic chat handler
        result = handle_subject_request(data)

        if result.get("success", False):
            return {
                "response": result.get("response", "No response generated"),
                "status": "success",
                "content_loaded": content["status"] == "success"
            }
        else:
            return {
                "response": result.get("response", "Error processing request"),
                "error": result.get("error", "Unknown error"),
                "status": "error",
                "content_loaded": content["status"] == "success"
            }

    except Exception as e:
        return {
            "response": "I apologize, but I'm unable to process your request at the moment. Please try again later.",
            "error": str(e),
            "status": "error",
            "content_loaded": False
        }

@app.options("/mail/chat")
async def respond_to_subject():
    return {
        "response": "I apologize, but I'm unable to process your request at the moment. Please try again later.",
    }

if __name__ == "__main__":
    import uvicorn

    # Get port from environment variable, default to 8100
    port = int(os.getenv('BACKEND_PORT', 8100))

    print(f"Starting Precision QA Backend on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)