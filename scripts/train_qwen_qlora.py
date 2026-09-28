"""One-epoch QLoRA SFT pilot for the SocraticLoop decision contract."""

from __future__ import annotations

import argparse
import json
from pathlib import Path


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="Qwen/Qwen2.5-Coder-3B-Instruct")
    parser.add_argument("--train", type=Path, default=Path("outputs/post_training/train.jsonl"))
    parser.add_argument("--validation", type=Path, default=Path("outputs/post_training/validation.jsonl"))
    parser.add_argument("--output", type=Path, default=Path("outputs/post_training/qwen_qlora_adapter"))
    args = parser.parse_args()

    import torch
    from datasets import Dataset
    from peft import LoraConfig
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig, TrainingArguments
    from trl import SFTTrainer

    tokenizer = AutoTokenizer.from_pretrained(args.model)
    quantization = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16)
    model = AutoModelForCausalLM.from_pretrained(args.model, device_map="auto", quantization_config=quantization)

    def load(path: Path) -> Dataset:
        rows = [json.loads(line) for line in path.read_text(encoding="utf-8").splitlines() if line]
        texts = []
        for row in rows:
            messages = [
                {"role": "user", "content": "Return the correct SocraticLoop decision JSON for this record:\n" + json.dumps(row["input"])},
                {"role": "assistant", "content": json.dumps(row["output"])},
            ]
            texts.append(tokenizer.apply_chat_template(messages, tokenize=False))
        return Dataset.from_dict({"text": texts})

    training = TrainingArguments(
        output_dir=str(args.output.parent / "checkpoints"),
        num_train_epochs=1,
        per_device_train_batch_size=1,
        per_device_eval_batch_size=1,
        gradient_accumulation_steps=4,
        learning_rate=2e-4,
        logging_steps=2,
        eval_strategy="epoch",
        save_strategy="no",
        report_to="none",
        fp16=True,
    )
    lora = LoraConfig(r=8, lora_alpha=16, lora_dropout=0.05, target_modules=["q_proj", "k_proj", "v_proj", "o_proj"], task_type="CAUSAL_LM")
    trainer = SFTTrainer(
        model=model,
        args=training,
        train_dataset=load(args.train),
        eval_dataset=load(args.validation),
        peft_config=lora,
        processing_class=tokenizer,
    )
    trainer.train()
    trainer.model.save_pretrained(args.output)
    tokenizer.save_pretrained(args.output)
    print(f"Saved QLoRA adapter to {args.output}")


if __name__ == "__main__":
    main()
