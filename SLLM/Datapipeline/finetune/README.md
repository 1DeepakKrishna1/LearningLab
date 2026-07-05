# Fine-tuning (Path B — LoRA / QLoRA)

This sub-pipeline fine-tunes a small base model on **your** documents so it adopts
your domain's tone, vocabulary, and task patterns. It complements RAG — it does
**not** replace it. Keep RAG for factual recall and citations; use the fine-tuned
model as the chat model behind RAG for better-styled answers.

## Hardware — it adapts to what you have

`train_qlora.py` no longer requires Unsloth, so it runs **with or without a GPU**:

| Hardware  | Mode                | Practical base model            |
|-----------|---------------------|---------------------------------|
| CPU only  | fp32 LoRA (slow)    | `Qwen/Qwen2.5-0.5B-Instruct` (default), up to ~1.5B |
| NVIDIA GPU| 4-bit QLoRA         | `meta-llama/Llama-3.2-3B-Instruct`, 7B–8B            |

> CPU training works but is slow. Keep the base model tiny, the dataset modest,
> and use `--max-steps 60` for a quick first run to confirm the flow end-to-end.

## Steps

```bash
# 0. Install torch for your hardware FIRST, then the rest:
#    CPU:  pip install torch --index-url https://download.pytorch.org/whl/cpu
#    GPU:  pick the CUDA build at https://pytorch.org/get-started/locally/
pip install -r requirements.txt
# (GPU only, for 4-bit QLoRA:)  pip install bitsandbytes

# 1. Generate an instruction dataset from your documents folder
#ollama pull llama3.2:3b
python build_dataset.py --folder ../data --out dataset.jsonl --per-chunk 3
or
python build_dataset.py --folder ../data --out dataset.jsonl --per-chunk 3 --model llama3.1:latest
or
python build_dataset.py --folder ../data --out dataset.jsonl --per-chunk 3 --model llama3.1:latest --max-chunks 25

# 2. REVIEW dataset.jsonl by hand and delete low-quality rows. This matters.

# 3. Fine-tune.
#    CPU (quick smoke test):
python train_qlora.py --data dataset.jsonl --max-steps 60
#    GPU (full run, larger base):
python train_qlora.py --data dataset.jsonl --base meta-llama/Llama-3.2-3B-Instruct --epochs 2

# 4. Convert the merged HF model to GGUF (no GPU needed):
git clone https://github.com/ggerganov/llama.cpp
pip install -r llama.cpp/requirements.txt
python llama.cpp/convert_hf_to_gguf.py outputs/merged --outfile outputs/model.gguf --outtype q8_0

# 5. Import the GGUF into Ollama
ollama create my-finetuned -f outputs/Modelfile

# 6. Tell the Backend to use it (Windows PowerShell)
$env:SLLM_CHAT_MODEL = "my-finetuned"
#    then start uvicorn as usual
```

## Why a dataset step?

A folder of PDFs/CSVs isn't training data. Supervised fine-tuning needs
`{instruction, input, output}` pairs. `build_dataset.py` synthesizes them from
your documents using a local Ollama model. Synthetic pairs are noisy — the manual
review in step 2 is the highest-leverage quality lever you have.

## Why not Unsloth?

Unsloth refuses to import without a CUDA accelerator (`NotImplementedError:
Unsloth cannot find any torch accelerator? You need a GPU.`). The HuggingFace +
PEFT stack here degrades gracefully to CPU instead, and Unsloth-prefixed model
ids (e.g. `unsloth/Meta-Llama-3.1-8B-Instruct`) are unnecessary — use the standard
`meta-llama/...` or `Qwen/...` repos.
