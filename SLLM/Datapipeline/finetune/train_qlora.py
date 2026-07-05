"""Stage B-2: LoRA / QLoRA fine-tune a small base model on the generated dataset.

Device-adaptive (no Unsloth, so it runs without a GPU):
  * CUDA GPU present  -> 4-bit QLoRA (bitsandbytes), can handle 3B-8B models.
  * CPU only          -> plain LoRA in fp32. WORKS but is slow; use a tiny base
                         model (0.5B-1.5B) and a small dataset, or just a few steps.

After training it merges the LoRA adapter into the base and saves a standard
HuggingFace model under outputs/merged. GGUF export is then a separate, GPU-free
step with llama.cpp (see the printed instructions / README) — Ollama imports the
resulting .gguf.

    # CPU-friendly default:
    python train_qlora.py --data dataset.jsonl

    # GPU (QLoRA), larger base:
    python train_qlora.py --data dataset.jsonl --base meta-llama/Llama-3.2-3B-Instruct --epochs 2
"""
import argparse
from pathlib import Path

import torch

# Alpaca-style fallback prompt for base models without a chat template.
ALPACA = (
    "Below is an instruction that describes a task, paired with an optional input. "
    "Write a response that appropriately completes the request.\n\n"
    "### Instruction:\n{instruction}\n\n### Input:\n{input}\n\n### Response:\n{output}"
)


def main() -> None:
    parser = argparse.ArgumentParser(description="Device-adaptive LoRA/QLoRA fine-tune")
    parser.add_argument("--data", type=Path, default=Path(__file__).with_name("dataset.jsonl"))
    # Default is a small, non-gated instruct model so it runs on CPU out of the box.
    parser.add_argument("--base", default="Qwen/Qwen2.5-0.5B-Instruct",
                        help="HF model id. CPU: stay <=1.5B. GPU: 3B-8B is fine.")
    parser.add_argument("--out", type=Path, default=Path(__file__).with_name("outputs"))
    parser.add_argument("--epochs", type=float, default=2)
    parser.add_argument("--max-steps", type=int, default=0, help="0 = use epochs; >0 caps steps")
    parser.add_argument("--max-seq-len", type=int, default=1024)
    parser.add_argument("--lr", type=float, default=2e-4)
    parser.add_argument("--batch", type=int, default=1)
    parser.add_argument("--grad-accum", type=int, default=8)
    args = parser.parse_args()

    if not args.data.exists():
        raise SystemExit(f"[error] dataset not found: {args.data} (run build_dataset.py first)")

    from datasets import load_dataset
    from peft import LoraConfig, get_peft_model, prepare_model_for_kbit_training
    from transformers import (
        AutoModelForCausalLM,
        AutoTokenizer,
        DataCollatorForLanguageModeling,
        Trainer,
        TrainingArguments,
    )

    use_cuda = torch.cuda.is_available()
    print(f"Device: {'CUDA GPU -> 4-bit QLoRA' if use_cuda else 'CPU -> fp32 LoRA (slow)'}")
    if not use_cuda:
        print("  [note] CPU training is slow. Keep --base small (e.g. Qwen/Qwen2.5-0.5B-Instruct),")
        print("         the dataset modest, and consider --max-steps 60 for a quick first run.")

    tokenizer = AutoTokenizer.from_pretrained(args.base)
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # --- Load the base model, 4-bit on GPU, plain fp32 on CPU. ---
    if use_cuda:
        from transformers import BitsAndBytesConfig

        bnb = BitsAndBytesConfig(
            load_in_4bit=True,
            bnb_4bit_quant_type="nf4",
            bnb_4bit_compute_dtype=torch.bfloat16,
            bnb_4bit_use_double_quant=True,
        )
        model = AutoModelForCausalLM.from_pretrained(
            args.base, quantization_config=bnb, device_map="auto",
        )
        model = prepare_model_for_kbit_training(model)
    else:
        model = AutoModelForCausalLM.from_pretrained(args.base, torch_dtype=torch.float32)

    model.config.use_cache = False

    # --- Attach LoRA adapters (the only thing we train). ---
    lora = LoraConfig(
        r=16, lora_alpha=16, lora_dropout=0.05, bias="none", task_type="CAUSAL_LM",
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
    )
    model = get_peft_model(model, lora)
    model.print_trainable_parameters()

    # --- Build + tokenize the dataset. ---
    has_chat_template = tokenizer.chat_template is not None

    def to_text(instruction, inp, out):
        if has_chat_template:
            user = instruction + (f"\n\n{inp}" if inp else "")
            return tokenizer.apply_chat_template(
                [{"role": "user", "content": user},
                 {"role": "assistant", "content": out}],
                tokenize=False,
            )
        return ALPACA.format(instruction=instruction, input=inp or "", output=out) + (tokenizer.eos_token or "")

    def tokenize(batch):
        texts = [to_text(i, x, o) for i, x, o in zip(batch["instruction"], batch["input"], batch["output"])]
        return tokenizer(texts, truncation=True, max_length=args.max_seq_len)

    dataset = load_dataset("json", data_files=str(args.data), split="train")
    dataset = dataset.map(tokenize, batched=True, remove_columns=dataset.column_names)
    print(f"Training on {len(dataset)} examples.")

    targs = TrainingArguments(
        per_device_train_batch_size=args.batch,
        gradient_accumulation_steps=args.grad_accum,
        num_train_epochs=args.epochs,
        max_steps=args.max_steps if args.max_steps > 0 else -1,
        learning_rate=args.lr,
        warmup_ratio=0.05,
        logging_steps=5,
        lr_scheduler_type="cosine",
        optim="adamw_8bit" if use_cuda else "adamw_torch",
        fp16=use_cuda,
        output_dir=str(args.out / "checkpoints"),
        report_to="none",
        seed=42,
    )

    trainer = Trainer(
        model=model,
        args=targs,
        train_dataset=dataset,
        data_collator=DataCollatorForLanguageModeling(tokenizer, mlm=False),
    )
    trainer.train()

    # --- Merge LoRA into the base and save a standard HF model. ---
    args.out.mkdir(parents=True, exist_ok=True)
    merged_dir = args.out / "merged"
    print(f"Merging adapter and saving merged model to {merged_dir} …")

    if use_cuda:
        # Can't merge into a 4-bit model; reload base in fp16 and merge there.
        from peft import PeftModel

        adapter_dir = args.out / "adapter"
        model.save_pretrained(adapter_dir)
        del model
        torch.cuda.empty_cache()
        base = AutoModelForCausalLM.from_pretrained(args.base, torch_dtype=torch.float16, device_map="cpu")
        merged = PeftModel.from_pretrained(base, adapter_dir).merge_and_unload()
    else:
        merged = model.merge_and_unload()

    merged.save_pretrained(merged_dir)
    tokenizer.save_pretrained(merged_dir)

    print("\nMerged HF model saved. Convert to GGUF for Ollama (no GPU needed):")
    print("  git clone https://github.com/ggerganov/llama.cpp")
    print("  pip install -r llama.cpp/requirements.txt")
    print(f"  python llama.cpp/convert_hf_to_gguf.py {merged_dir} \\")
    print(f"         --outfile {args.out / 'model.gguf'} --outtype q8_0")
    print(f"\nThen import:  ollama create my-finetuned -f {args.out / 'Modelfile'}")

    # Write a Modelfile the user can use once model.gguf exists.
    (args.out / "Modelfile").write_text(
        "FROM ./model.gguf\n"
        "PARAMETER temperature 0.3\n"
        "PARAMETER num_ctx 8192\n"
        'SYSTEM """You are a helpful assistant fine-tuned on the provided domain documents."""\n',
        encoding="utf-8",
    )


if __name__ == "__main__":
    main()
