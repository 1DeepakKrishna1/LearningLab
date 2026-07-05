import os
from fastapi import APIRouter
from models import ChatRequest
from dotenv import load_dotenv

load_dotenv()
router = APIRouter()

GROQ_API_KEY = os.getenv("GROQ_API_KEY", "")

SYSTEM_PROMPT = """You are WorkflowAI, an intelligent assistant embedded in a visual workflow management system.

The system lets users orchestrate automated workflows using Agents (processing units) and Tools (capabilities).

Agent types:
- automatic: fully automated steps
- role_based: routed to specific team roles
- human_in_the_loop: pauses for human approval
- conditional: branches based on conditions
- parallel: runs sub-tasks concurrently

Your job is to:
- Help users design effective workflows
- Explain what agents and tools do
- Suggest improvements or missing steps
- Interpret execution results
- Answer questions about best practices

Keep answers concise and actionable. When a workflow context is provided, tailor your response to it."""


def _fallback_response(message: str) -> str:
    msg_lower = message.lower()
    if any(w in msg_lower for w in ["help", "what", "how", "explain"]):
        return (
            "I'm your WorkflowAI assistant! I can help you design workflows, configure agents, "
            "and interpret execution results. To use the full AI, add your GROQ_API_KEY to backend/.env."
        )
    if any(w in msg_lower for w in ["add", "create", "suggest"]):
        return (
            "To build a workflow: drag agents from the left panel onto the canvas, "
            "connect them with edges, configure properties in the right panel, then click Run."
        )
    return (
        "I'm ready to help with your workflow! Set GROQ_API_KEY in backend/.env to enable full AI responses. "
        "In the meantime, feel free to ask about workflow design and I'll do my best."
    )


@router.post("/chat")
async def chat(body: ChatRequest):
    if not GROQ_API_KEY:
        return {"message": _fallback_response(body.message)}

    try:
        from groq import Groq
        client = Groq(api_key=GROQ_API_KEY)

        context_str = ""
        if body.workflow_context:
            ctx = body.workflow_context
            context_str = (
                f"\n\nCurrent workflow: \"{ctx.get('name', 'Untitled')}\"\n"
                f"Description: {ctx.get('description', 'N/A')}\n"
                f"Agents: {', '.join(a['name'] for a in ctx.get('agents', []))}\n"
                f"Connections: {ctx.get('connections', 0)}"
            )

        messages = [{"role": "system", "content": SYSTEM_PROMPT + context_str}]
        for h in (body.history or [])[-10:]:
            messages.append({"role": h.role, "content": h.content})
        messages.append({"role": "user", "content": body.message})

        completion = client.chat.completions.create(
            model="llama-3.3-70b-versatile",
            messages=messages,
            max_tokens=512,
            temperature=0.7,
        )
        return {"message": completion.choices[0].message.content}

    except Exception as exc:
        return {"message": f"AI service error: {str(exc)}. Please check your GROQ_API_KEY."}
