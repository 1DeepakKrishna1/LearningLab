#!/usr/bin/env python3
"""LLM-backed routing for the skill runtime.

Given a natural-language task and the list of discovered skills, ask an LLM
(OpenAI or Gemini) to choose the single best-matching skill. Returns the chosen
skill name as a string, or None when no provider is configured or the request
fails -- the runtime then falls back to keyword matching, so everything still
works offline.

Configuration (environment variables):
    SKILL_ROUTER     openai | gemini | keyword | auto   (default: auto)
    OPENAI_API_KEY   required for the OpenAI provider
    OPENAI_MODEL     default: gpt-4o-mini
    GEMINI_API_KEY   (or GOOGLE_API_KEY) required for the Gemini provider
    GEMINI_MODEL     default: gemini-2.0-flash

Only the Python standard library is used: requests go through urllib so the
runtime stays dependency-free.
"""

import json
import os
import sys
import urllib.error
import urllib.request
from pathlib import Path


def load_dotenv(path=None):
    """Load KEY=VALUE pairs from a .env file into os.environ.

    Dependency-free (no python-dotenv). Existing environment variables take
    precedence, so a real shell export always wins over the file. Lines that
    are blank, comments (#), or lack an '=' are ignored; surrounding quotes and
    a leading 'export ' are stripped from values.
    """
    env_path = Path(path) if path else Path(__file__).with_name(".env")
    if not env_path.exists():
        return
    for raw in env_path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        if line.startswith("export "):
            line = line[len("export "):]
        key, _, value = line.partition("=")
        key = key.strip()
        value = value.strip().strip('"').strip("'")
        if key and key not in os.environ:
            os.environ[key] = value


# Populate os.environ from .env as soon as the router is imported, before any
# key lookups happen.
load_dotenv()

PROMPT_TEMPLATE = """\
You are the router for a command-line skill system. Choose the single skill \
whose description best matches the user's task.

Respond with ONLY the skill's name, copied exactly from the list, and nothing \
else. If no skill is a reasonable match, respond with the single word NONE.

Task: {task}

Available skills:
{skill_list}
"""


def _provider():
    """Resolve which provider to use from SKILL_ROUTER and available keys."""
    choice = os.environ.get("SKILL_ROUTER", "auto").lower()
    if choice in ("openai", "gemini", "keyword"):
        return choice
    # auto: prefer OpenAI if its key is set, else Gemini, else fall back.
    if os.environ.get("OPENAI_API_KEY"):
        return "openai"
    if os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY"):
        return "gemini"
    return "keyword"


def _build_prompt(task, skills):
    skill_list = "\n".join(
        f"- {s['name']}: {s['description']}" for s in skills
    )
    return PROMPT_TEMPLATE.format(task=task, skill_list=skill_list)


def _post_json(url, payload, headers, timeout=30):
    """POST a JSON body and return the parsed JSON response."""
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return json.loads(resp.read().decode("utf-8"))


def _route_openai(prompt):
    key = os.environ.get("OPENAI_API_KEY")
    if not key:
        raise RuntimeError("OPENAI_API_KEY is not set")
    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0,
        "max_tokens": 20,
    }
    headers = {
        "Authorization": f"Bearer {key}",
        "Content-Type": "application/json",
    }
    data = _post_json(
        "https://api.openai.com/v1/chat/completions", payload, headers
    )
    return data["choices"][0]["message"]["content"]


def _route_gemini(prompt):
    key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not key:
        raise RuntimeError("GEMINI_API_KEY (or GOOGLE_API_KEY) is not set")
    model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    url = (
        "https://generativelanguage.googleapis.com/v1beta/models/"
        f"{model}:generateContent?key={key}"
    )
    payload = {
        "contents": [{"parts": [{"text": prompt}]}],
        "generationConfig": {"temperature": 0, "maxOutputTokens": 20},
    }
    headers = {"Content-Type": "application/json"}
    data = _post_json(url, payload, headers)
    return data["candidates"][0]["content"]["parts"][0]["text"]


def _match_name(reply, skills):
    """Map a raw LLM reply back to a known skill name (case-insensitive)."""
    reply = (reply or "").strip().strip(".\"'` ").lower()
    if not reply or reply == "none":
        return None
    by_name = {s["name"].lower(): s["name"] for s in skills}
    if reply in by_name:
        return by_name[reply]
    # Be lenient: the model may wrap the name in a sentence.
    for name_lower, name in by_name.items():
        if name_lower in reply:
            return name
    return None


def llm_route(task, skills, provider=None):
    """Return (skill_name, detail) chosen by an LLM, or None to fall back.

    `detail` is a short human-readable string describing how the choice was
    made, for the runtime to print.
    """
    provider = provider or _provider()
    if provider == "keyword":
        return None

    prompt = _build_prompt(task, skills)
    try:
        if provider == "openai":
            reply = _route_openai(prompt)
        elif provider == "gemini":
            reply = _route_gemini(prompt)
        else:
            return None
    except (urllib.error.URLError, RuntimeError, KeyError, ValueError) as exc:
        print(f"warning: {provider} routing failed ({exc}); "
              "falling back to keyword matching", file=sys.stderr)
        return None

    name = _match_name(reply, skills)
    if not name:
        return None
    return name, f"{provider} chose this"
