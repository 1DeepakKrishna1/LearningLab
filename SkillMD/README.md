# Skill Runtime

A tiny, dependency-free runtime that demonstrates the three jobs of a skill
system: **discover** skills from disk, **route** a natural-language task to the
best-matching one, and **execute** its script.

## Layout

```
runtime.py                       # the discover / route / execute engine
skills/
  <skill-name>/
    SKILL.md                     # frontmatter (name, description, entrypoint) + docs
    scripts/<entrypoint>.py      # the script the runtime runs
```

Each skill lives in its own folder under `skills/`. The runtime finds a skill by
globbing for `skills/*/SKILL.md`, parses the frontmatter, and runs the declared
`entrypoint` (relative to the skill folder) when that skill is selected.

## Bundled skills

| Skill           | What it does                                          |
| --------------- | ----------------------------------------------------- |
| `todo-manager`  | Persistent CLI to-do list (add/list/done/remove/clear)|
| `text-stats`    | Word, line, and character counts                      |
| `calc`          | Safely evaluate arithmetic / math expressions         |
| `password-gen`  | Generate strong random passwords or passphrases       |
| `json-tool`     | Validate, pretty-print, or minify JSON                |
| `case-convert`  | Convert text between cases (snake, kebab, camel, ...)  |

## Usage

```bash
python runtime.py list                         # list discovered skills
python runtime.py show calc                    # print a skill's SKILL.md body

# Route a task to a skill and forward args after `--` to its script:
python runtime.py run --task "track my tasks"        -- add "Buy milk"
python runtime.py run --task "how many words is this" -- "hello there world"
python runtime.py run --task "calculate this"        -- "sqrt(144) + pi"
python runtime.py run --task "generate a password"   -- --length 24
python runtime.py run --task "format this json"      -- format '{"b":2,"a":1}'
python runtime.py run --task "make this snake case"  -- snake "Hello World"
```

## Routing

By default the runtime routes with an **LLM** when one is configured, and falls
back to **keyword overlap** (task vs. each skill's `name` + `description`)
otherwise — so it always works offline.

LLM routing lives in `router.py` and supports OpenAI and Gemini via their REST
APIs (no SDKs — calls go through `urllib`, keeping the project dependency-free).
Configure it with environment variables:

| Variable          | Purpose                                            | Default            |
| ----------------- | -------------------------------------------------- | ------------------ |
| `SKILL_ROUTER`    | `openai` \| `gemini` \| `keyword` \| `auto`        | `auto`             |
| `OPENAI_API_KEY`  | API key for the OpenAI provider                    | —                  |
| `OPENAI_MODEL`    | OpenAI model                                       | `gpt-4o-mini`      |
| `GEMINI_API_KEY`  | API key for Gemini (`GOOGLE_API_KEY` also honored) | —                  |
| `GEMINI_MODEL`    | Gemini model                                       | `gemini-2.0-flash` |

These can be set in the shell or placed in a `.env` file in the project root —
`router.py` loads it automatically (no `python-dotenv` needed). Copy
`.env.example` to `.env` and fill in your keys. Real shell environment variables
take precedence over `.env`, and `.env` is git-ignored so keys aren't committed.

In `auto` mode the runtime uses OpenAI if `OPENAI_API_KEY` is set, else Gemini
if its key is set, else keyword matching. If an LLM call fails (no key, network
error, bad response) it logs a warning and falls back to keyword matching.

```bash
# Route with OpenAI:
SKILL_ROUTER=openai OPENAI_API_KEY=sk-... \
  python runtime.py run --task "tidy up this json" -- format '{"b":2,"a":1}'

# Route with Gemini:
SKILL_ROUTER=gemini GEMINI_API_KEY=... \
  python runtime.py run --task "make a strong secret" -- --length 24
```

## Adding a skill

1. Create `skills/<name>/SKILL.md` with `name`, `description`, and `entrypoint`
   frontmatter. Write a clear, trigger-rich `description` — that text is what
   routing matches against.
2. Add the script at the path named by `entrypoint` (conventionally
   `scripts/<name>.py`).
3. Run `python runtime.py list` to confirm it's discovered.
