#!/usr/bin/env python3
"""A tiny skill runtime.

It does three things at runtime:
  1. DISCOVER  - scan the skills/ folder for SKILL.md files and parse them.
  2. ROUTE     - read each skill's description and pick the best match for a task.
  3. EXECUTE   - run the matched skill's script, forwarding any arguments.

Usage:
    python runtime.py list
    python runtime.py show todo-manager
    python runtime.py run --task "I want to track my tasks" -- add "Buy milk"
    python runtime.py run --task "how many words is this" -- "hello there world"
"""

import argparse
import re
import subprocess
import sys
from pathlib import Path

import router

SKILLS_DIR = Path(__file__).with_name("skills")

# Words too common to be useful when matching a task to a skill description.
STOPWORDS = {
    "a", "an", "the", "to", "of", "in", "on", "is", "it", "this", "that",
    "i", "my", "me", "want", "need", "how", "many", "do", "with", "for",
    "and", "or", "please", "can", "you",
}


def parse_skill_md(path):
    """Parse a SKILL.md into {name, description, entrypoint, body}.

    Only handles the simple `key: value` frontmatter format used here, so no
    external YAML library is required.
    """
    text = path.read_text()
    meta = {"name": path.parent.name, "description": "", "entrypoint": None}
    body = text
    if text.startswith("---"):
        # Split off the frontmatter block between the first two '---' markers.
        _, frontmatter, body = text.split("---", 2)
        for line in frontmatter.strip().splitlines():
            if ":" in line:
                key, _, value = line.partition(":")
                meta[key.strip()] = value.strip()
    meta["body"] = body.strip()
    return meta


def discover_skills(skills_dir=SKILLS_DIR):
    """Find every folder under skills_dir that contains a SKILL.md."""
    skills = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        info = parse_skill_md(skill_md)
        info["dir"] = skill_md.parent
        skills.append(info)
    return skills


def _tokenize(text):
    words = re.findall(r"[a-z0-9]+", text.lower())
    return {w for w in words if w not in STOPWORDS}


def keyword_route(task, skills):
    """Pick the skill whose name + description best overlaps the task.

    Returns (best_skill, detail). This is the offline fallback: the runtime
    *reading the SKILL.md descriptions* and scoring word overlap.
    """
    task_words = _tokenize(task)
    best, best_score = None, 0
    for skill in skills:
        haystack = _tokenize(skill["name"] + " " + skill["description"])
        score = len(task_words & haystack)
        if score > best_score:
            best, best_score = skill, score
    if not best:
        return None, None
    return best, f"keyword match score: {best_score}"


def route(task, skills):
    """Route a task to a skill, preferring an LLM when one is configured.

    Returns (skill, detail). Asks router.llm_route() first (OpenAI or Gemini,
    per the SKILL_ROUTER env var); if no provider is configured or the call
    fails, falls back to keyword matching so the runtime always works offline.
    """
    by_name = {s["name"]: s for s in skills}
    chosen = router.llm_route(task, skills)
    if chosen:
        name, detail = chosen
        return by_name.get(name), detail
    return keyword_route(task, skills)


def execute(skill, args):
    """Run the skill's entrypoint script, forwarding args to it."""
    entry = skill.get("entrypoint")
    if not entry:
        # Fall back to the single .py file under scripts/ if none is declared.
        candidates = list((skill["dir"] / "scripts").glob("*.py"))
        if len(candidates) != 1:
            sys.exit(f"Cannot determine entrypoint for '{skill['name']}'.")
        entry = candidates[0].relative_to(skill["dir"])
    script = skill["dir"] / entry
    cmd = [sys.executable, str(script), *args]
    print(f">> executing {skill['name']}: {' '.join(cmd[1:])}\n")
    return subprocess.run(cmd, cwd=skill["dir"]).returncode


def cmd_list(_):
    skills = discover_skills()
    if not skills:
        print(f"No skills found in {SKILLS_DIR}")
        return
    print(f"Discovered {len(skills)} skill(s):\n")
    for s in skills:
        print(f"  {s['name']}")
        print(f"    {s['description']}\n")


def cmd_show(args):
    skills = {s["name"]: s for s in discover_skills()}
    skill = skills.get(args.name)
    if not skill:
        sys.exit(f"No skill named '{args.name}'")
    print(skill["body"])


def cmd_run(args):
    skills = discover_skills()
    skill, detail = route(args.task, skills)
    if not skill:
        sys.exit("No skill matched that task.")
    print(f"routed '{args.task}' -> '{skill['name']}' ({detail})")
    sys.exit(execute(skill, args.script_args))


def main():
    parser = argparse.ArgumentParser(description="A tiny skill runtime.")
    sub = parser.add_subparsers(dest="command", required=True)

    p_list = sub.add_parser("list", help="list discovered skills")
    p_list.set_defaults(func=cmd_list)

    p_show = sub.add_parser("show", help="print a skill's SKILL.md body")
    p_show.add_argument("name")
    p_show.set_defaults(func=cmd_show)

    p_run = sub.add_parser("run", help="route a task to a skill and run its script")
    p_run.add_argument("--task", required=True, help="natural-language task")
    p_run.add_argument(
        "script_args",
        nargs="*",
        help="arguments after -- are forwarded to the skill's script",
    )
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args()
    args.func(args)


if __name__ == "__main__":
    main()
