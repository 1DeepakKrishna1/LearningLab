"""
reasoning_techniques.py

A single registry of prompt-engineering reasoning techniques, each with:
  - system        : the persistent system-prompt instruction
  - user_template : the per-request user prompt with {placeholders}
  - example       : a fully filled-in user prompt for reference

Two techniques (self_consistency, tree_of_thoughts) are multi-call patterns.
Their dict carries an extra "orchestration" note explaining the loop that
lives in application code rather than in a single prompt.

Usage (e.g. with Ollama):

    from reasoning_techniques import TECHNIQUES, build_prompt

    t = TECHNIQUES["chain_of_thought"]
    system = t["system"]
    user   = build_prompt("chain_of_thought", problem_statement="...")

    # send `system` and `user` to your model
"""

import json
import os
from pathlib import Path
from string import Formatter
from typing import Any


def _load_env() -> None:
    """Load OPENAI_API_KEY / OPENAI_MODEL (and others) from a local .env file.

    Uses python-dotenv if available; otherwise falls back to a minimal parser
    so the .env file still works without the extra dependency. Existing
    environment variables are not overwritten.
    """
    env_path = Path(__file__).resolve().parent / ".env"

    try:
        from dotenv import load_dotenv
        load_dotenv(env_path)
        return
    except ImportError:
        pass

    if not env_path.exists():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        key, value = key.strip(), value.strip().strip("'\"")
        os.environ.setdefault(key, value)


_load_env()


def _load_techniques() -> dict[str, dict[str, Any]]:
    techniques_path = Path(__file__).resolve().parent / "techniques.json"
    with techniques_path.open("r", encoding="utf-8") as f:
        return json.load(f)


TECHNIQUES: dict[str, dict[str, Any]] = _load_techniques()


# Techniques whose real behavior depends on an application-side loop.
MULTI_CALL_TECHNIQUES = ("self_consistency", "tree_of_thoughts")


def required_fields(technique: str) -> list[str]:
    """Return the {placeholder} names in a technique's user_template."""
    template = TECHNIQUES[technique]["user_template"]
    return [
        name
        for _, name, _, _ in Formatter().parse(template)
        if name is not None
    ]


def build_prompt(technique: str, **fillers: Any) -> str:
    """
    Fill a technique's user_template with the given values.

    Raises KeyError if the technique is unknown, and ValueError if any
    required placeholder is missing.
    """
    if technique not in TECHNIQUES:
        raise KeyError(
            f"Unknown technique '{technique}'. "
            f"Available: {', '.join(TECHNIQUES)}"
        )
    needed = set(required_fields(technique))
    missing = needed - set(fillers)
    if missing:
        raise ValueError(
            f"Missing fillers for '{technique}': {', '.join(sorted(missing))}"
        )
    return TECHNIQUES[technique]["user_template"].format(**fillers)


def _choose_technique() -> str | None:
    """Print a numbered menu of techniques and return the chosen key.

    Returns None if the user chooses to quit.
    """
    names = list(TECHNIQUES)

    print("Available reasoning techniques:\n")
    for i, name in enumerate(names, start=1):
        flag = "  [multi-call]" if name in MULTI_CALL_TECHNIQUES else ""
        print(f"  {i:>2}. {name}{flag}")
    print()

    while True:
        choice = input(f"Choose a technique [1-{len(names)}] (q to quit): ").strip()
        if choice.lower() in ("q", "quit", "exit"):
            return None
        if choice.isdigit() and 1 <= int(choice) <= len(names):
            return names[int(choice) - 1]
        # Also accept the technique name directly.
        if choice in TECHNIQUES:
            return choice
        print("  Invalid selection, try again.\n")


def _prompt_for_fields(technique: str) -> dict[str, str]:
    """Ask the user for a value for each placeholder in the technique."""
    fields = required_fields(technique)
    if not fields:
        return {}

    print("\nProvide a value for each required field.")
    print("(Use \\n in your input to insert a line break.)\n")

    fillers: dict[str, str] = {}
    for field in fields:
        while True:
            value = input(f"  {field}: ").strip()
            if value:
                fillers[field] = value.replace("\\n", "\n")
                break
            print("    This field is required, please enter a value.")
    return fillers


def _ask_yes_no(question: str) -> bool:
    """Prompt for a yes/no answer; default is no."""
    while True:
        answer = input(f"{question} [y/N]: ").strip().lower()
        if answer in ("y", "yes"):
            return True
        if answer in ("", "n", "no"):
            return False
        print("  Please answer 'y' or 'n'.")


def _print_response(text: str | None) -> None:
    """Render a model response in a framed section."""
    print("=" * 70)
    print("MODEL RESPONSE")
    print("=" * 70)
    print(text)
    print()


def _execute_openai(system: str, user: str) -> None:
    """Send the prompt to OpenAI.

    Requires the `openai` package and OPENAI_API_KEY. Model overridable with
    OPENAI_MODEL (defaults to gpt-4o-mini).
    """
    try:
        from openai import OpenAI
    except ImportError:
        print(
            "\nThe 'openai' package is not installed. "
            "Install it with:  pip install openai"
        )
        return

    if not os.environ.get("OPENAI_API_KEY"):
        print(
            "\nOPENAI_API_KEY is not set. Add it to your .env file or environment, "
            "e.g.:\n  OPENAI_API_KEY=sk-..."
        )
        return

    model = os.environ.get("OPENAI_MODEL", "gpt-4o-mini")
    print(f"\nExecuting with OpenAI model '{model}' ...\n")

    try:
        client = OpenAI()
        response = client.chat.completions.create(
            model=model,
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        )
    except Exception as exc:  # network/auth/quota errors, etc.
        print(f"OpenAI request failed: {exc}")
        return

    _print_response(response.choices[0].message.content)


def _execute_gemini(system: str, user: str) -> None:
    """Send the prompt to Google Gemini.

    Requires the `google-genai` package and GEMINI_API_KEY (GOOGLE_API_KEY is
    also accepted). Model overridable with GEMINI_MODEL (defaults to
    gemini-2.0-flash).
    """
    try:
        from google import genai
        from google.genai import types
    except ImportError:
        print(
            "\nThe 'google-genai' package is not installed. "
            "Install it with:  pip install google-genai"
        )
        return

    api_key = os.environ.get("GEMINI_API_KEY") or os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        print(
            "\nGEMINI_API_KEY is not set. Add it to your .env file or environment, "
            "e.g.:\n  GEMINI_API_KEY=..."
        )
        return

    model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    print(f"\nExecuting with Gemini model '{model}' ...\n")

    try:
        client = genai.Client(api_key=api_key)
        response = client.models.generate_content(
            model=model,
            contents=user,
            config=types.GenerateContentConfig(system_instruction=system),
        )
    except Exception as exc:  # network/auth/quota errors, etc.
        print(f"Gemini request failed: {exc}")
        return

    _print_response(response.text)


# Registry of supported execution providers.
PROVIDERS = {
    "openai": _execute_openai,
    "gemini": _execute_gemini,
}


def execute_prompt(system: str, user: str, provider: str = "openai") -> None:
    """Dispatch the system + user prompt to the chosen provider."""
    runner = PROVIDERS.get(provider)
    if runner is None:
        print(f"Unknown provider '{provider}'. Choices: {', '.join(PROVIDERS)}")
        return
    runner(system, user)


def _choose_provider() -> str | None:
    """Ask which provider to execute with; returns None to cancel."""
    names = list(PROVIDERS)
    default = os.environ.get("LLM_PROVIDER", names[0]).lower()
    if default not in PROVIDERS:
        default = names[0]

    options = "  ".join(
        f"{i}. {name}" for i, name in enumerate(names, start=1)
    )
    while True:
        choice = input(
            f"Provider: {options}  [Enter={default}, c=cancel]: "
        ).strip().lower()
        if choice == "c":
            return None
        if choice == "":
            return default
        if choice.isdigit() and 1 <= int(choice) <= len(names):
            return names[int(choice) - 1]
        if choice in PROVIDERS:
            return choice
        print("  Invalid selection, try again.")


def _run_one(technique: str) -> None:
    """Fill fields for a technique, render the prompts, optionally execute."""
    spec = TECHNIQUES[technique]

    print(f"\nSelected: {technique}")
    if technique in MULTI_CALL_TECHNIQUES:
        print("Note: this is a multi-call pattern (see orchestration note below).")

    fillers = _prompt_for_fields(technique)
    system_prompt = spec["system"]
    user_prompt = build_prompt(technique, **fillers)

    print("\n" + "=" * 70)
    print("SYSTEM PROMPT")
    print("=" * 70)
    print(system_prompt)

    print("\n" + "=" * 70)
    print("USER PROMPT")
    print("=" * 70)
    print(user_prompt)

    if technique in MULTI_CALL_TECHNIQUES and "orchestration" in spec:
        print("\n" + "=" * 70)
        print("ORCHESTRATION (application-side loop)")
        print("=" * 70)
        print(spec["orchestration"])

    print()
    if _ask_yes_no("Execute this prompt with an LLM?"):
        provider = _choose_provider()
        if provider is not None:
            execute_prompt(system_prompt, user_prompt, provider)


def run_cli() -> None:
    """Interactive loop: choose a technique, build prompts, optionally execute.

    Repeats until the user chooses to quit at the technique menu.
    """
    print("=" * 70)
    print("  Reasoning Technique Prompt Builder")
    print("=" * 70 + "\n")

    while True:
        technique = _choose_technique()
        if technique is None:
            print("\nGoodbye.")
            return
        _run_one(technique)
        print("-" * 70 + "\n")


if __name__ == "__main__":
    try:
        run_cli()
    except (KeyboardInterrupt, EOFError):
        print("\nCancelled.")
        raise SystemExit(130)
