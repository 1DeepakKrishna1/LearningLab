"""Stage B-1: turn your documents into a supervised fine-tuning dataset.

Raw PDFs/CSVs are not training data. This script reads the same folder the RAG
pipeline uses, chunks it, and asks a local Ollama model to synthesize
instruction/response pairs grounded in each chunk. The output is JSONL of
{"instruction", "input", "output"} — exactly the shape train_qlora.py expects.

Review the generated dataset before training. Synthetic data is noisy; deleting
bad rows is the single highest-leverage thing you can do for quality.

Usage:
    python build_dataset.py                       # uses parent config.DOCS_FOLDER
    python build_dataset.py --folder ../data --out dataset.jsonl --per-chunk 3

Prerequisites:
    ollama serve
    ollama pull llama3.2:3b      # or any chat model; bigger = better pairs
"""
import argparse
import json
import sys
from pathlib import Path

from ollama import Client
from tqdm import tqdm

# Reuse the parent pipeline's loaders/chunker/config.
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
import config  # noqa: E402
from chunker import chunk_text  # noqa: E402
from loaders import load_file  # noqa: E402

GEN_PROMPT = """You are creating a fine-tuning dataset. Read the CONTEXT below and \
write {n} diverse question/answer pairs that can be answered SOLELY from it.

Rules:
- Questions must be self-contained (do not say "according to the context").
- Answers must be fully grounded in the context — never invent facts.
- Vary the style: factual, how-to, summarization.
- Respond with ONLY a JSON array, no prose, like:
[{{"instruction": "...", "output": "..."}}]

CONTEXT:
{chunk}
"""


def _as_text(value) -> str:
    """Coerce a model-produced field into a clean string.

    The LLM sometimes returns 'output'/'instruction' as a list (e.g. steps) or a
    nested object instead of a string, which broke .strip(). Normalize all of it.
    """
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    if isinstance(value, list):
        return "\n".join(_as_text(v) for v in value).strip()
    if isinstance(value, dict):
        return "\n".join(f"{k}: {_as_text(v)}" for k, v in value.items()).strip()
    return str(value).strip()


def _extract_json_array(text: str):
    """Best-effort: pull the first [...] block out of the model's reply."""
    start = text.find("[")
    end = text.rfind("]")
    if start == -1 or end == -1 or end < start:
        return []
    try:
        data = json.loads(text[start : end + 1])
        return data if isinstance(data, list) else []
    except json.JSONDecodeError:
        return []


def main() -> None:
    parser = argparse.ArgumentParser(description="Build a QLoRA instruction dataset from documents")
    parser.add_argument("--folder", type=Path, default=config.DOCS_FOLDER)
    parser.add_argument("--out", type=Path, default=Path(__file__).with_name("dataset.jsonl"))
    parser.add_argument("--model", default=config.__dict__.get("GEN_MODEL", "llama3.2:3b"))
    parser.add_argument("--per-chunk", type=int, default=3, help="Q&A pairs per chunk")
    parser.add_argument("--max-chunks", type=int, default=0, help="0 = no limit")
    args = parser.parse_args()

    folder = args.folder.resolve()
    files = sorted(
        p for p in folder.rglob("*")
        if p.is_file() and p.suffix.lower() in config.SUPPORTED_SUFFIXES
    )
    if not files:
        sys.exit(f"[error] no supported files under {folder}")

    chunks = []
    for path in files:
        rel = path.relative_to(folder)
        for c in chunk_text(load_file(path), config.CHUNK_SIZE, config.CHUNK_OVERLAP):
            chunks.append((str(rel), c))
    if args.max_chunks:
        chunks = chunks[: args.max_chunks]

    print(f"{len(files)} file(s) -> {len(chunks)} chunk(s). Generating with '{args.model}'…")
    ollama = Client(host=config.OLLAMA_HOST)

    # Preflight: confirm the generation model is actually pulled, so we fail fast
    # with a clear message instead of emitting one 404 warning per chunk.
    try:
        ollama.chat(model=args.model, messages=[{"role": "user", "content": "ping"}])
    except Exception as exc:  # noqa: BLE001
        sys.exit(
            f"\n[error] cannot use model '{args.model}': {exc}\n"
            f"        Pull it first:   ollama pull {args.model}\n"
            f"        Or pass one you already have, e.g.:  "
            f"python build_dataset.py --model llama3.1:latest"
        )

    rows, kept = 0, 0
    with args.out.open("w", encoding="utf-8") as fh:
        for source, chunk in tqdm(chunks, unit="chunk"):
            prompt = GEN_PROMPT.format(n=args.per_chunk, chunk=chunk)
            try:
                resp = ollama.chat(
                    model=args.model,
                    messages=[{"role": "user", "content": prompt}],
                    options={"temperature": 0.7},
                )
                pairs = _extract_json_array(resp["message"]["content"])
            except Exception as exc:  # noqa: BLE001
                print(f"  [warn] generation failed for {source}: {exc}")
                pairs = []

            for p in pairs:
                if not isinstance(p, dict):
                    continue
                instr = _as_text(p.get("instruction"))
                out = _as_text(p.get("output"))
                if not instr or not out:
                    continue
                fh.write(json.dumps(
                    {"instruction": instr, "input": "", "output": out, "source": source},
                    ensure_ascii=False,
                ) + "\n")
                kept += 1
            rows += 1

    print(f"\nWrote {kept} instruction pair(s) to {args.out}")
    print("REVIEW the file and remove bad rows before running train_qlora.py.")


if __name__ == "__main__":
    main()
