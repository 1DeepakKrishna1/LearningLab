from fastapi import APIRouter
import os

router = APIRouter()

@router.post("/chat")
def chat(body: dict):
    message = body.get("message", "")
    # use OpenAI if API key provided, otherwise echo stub response
    # allow either OpenAI or GROQ style environment variable
    api_key = os.getenv("OPENAI_API_KEY") or os.getenv("GROQ_API_KEY")
    if api_key:
        try:
            import openai
            openai.api_key = api_key
            resp = openai.ChatCompletion.create(
                model="gpt-3.5-turbo",
                messages=[
                    {"role": "user", "content": message}
                ]
            )
            text = resp.choices[0].message.content
            return {"response": text}
        except Exception as e:
            return {"response": f"(error calling OpenAI: {e})"}
    else:
        # simple echo / placeholder
        return {"response": f"AI stub received: {message}"}
