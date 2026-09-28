"""Run the Qwen baseline or SocraticLoop system on the executable benchmark."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import re
import sys
import time

ROOT = Path(__file__).parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from socratic_loop.agent_benchmark import load_cases, model_prompt, prepare_workspaces


def parse_json(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        return {"rationale": text, "parse_error": "missing_json_object"}
    try:
        return json.loads(match.group())
    except json.JSONDecodeError:
        return {"rationale": text, "parse_error": "invalid_json_object"}


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system", choices=("qwen_raw", "qwen_harness", "qwen_qlora_harness"), required=True)
    parser.add_argument("--model", default="Qwen/Qwen2.5-Coder-3B-Instruct")
    parser.add_argument("--adapter", help="PEFT adapter path; required for qwen_qlora_harness")
    parser.add_argument("--workspaces", type=Path, default=Path("outputs/agent_benchmark/workspaces"))
    parser.add_argument("--output", type=Path, default=Path("outputs/agent_benchmark/responses"))
    args = parser.parse_args()
    if args.system == "qwen_qlora_harness" and not args.adapter:
        parser.error("--adapter is required for qwen_qlora_harness")

    import torch
    from transformers import AutoModelForCausalLM, AutoTokenizer, BitsAndBytesConfig

    quantization = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_quant_type="nf4", bnb_4bit_compute_dtype=torch.float16)
    tokenizer = AutoTokenizer.from_pretrained(args.model)
    model = AutoModelForCausalLM.from_pretrained(args.model, device_map="auto", quantization_config=quantization)
    if args.adapter:
        from peft import PeftModel
        model = PeftModel.from_pretrained(model, args.adapter)

    prepare_workspaces(args.workspaces)
    rows = []
    for case in load_cases():
        prompt = model_prompt(args.system, case, args.workspaces / case["id"])
        messages = [{"role": "user", "content": prompt}]
        rendered = tokenizer.apply_chat_template(messages, tokenize=False, add_generation_prompt=True)
        inputs = tokenizer([rendered], return_tensors="pt").to(model.device)
        started = time.perf_counter()
        with torch.inference_mode():
            generated = model.generate(**inputs, max_new_tokens=220, do_sample=False, pad_token_id=tokenizer.eos_token_id)
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        new_tokens = generated[0][inputs.input_ids.shape[1]:]
        text = tokenizer.decode(new_tokens, skip_special_tokens=True)
        rows.append({
            "scenario_id": case["id"],
            **parse_json(text),
            "latency_ms": latency_ms,
            "tool_calls": 1,
            "input_tokens": int(inputs.input_ids.shape[1]),
            "output_tokens": int(new_tokens.shape[0]),
            "model": args.model,
            "adapter": args.adapter,
        })

    args.output.mkdir(parents=True, exist_ok=True)
    target = args.output / f"{args.system}.jsonl"
    target.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    print(f"Wrote {len(rows)} responses to {target}")


if __name__ == "__main__":
    main()
