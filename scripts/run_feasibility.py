"""Run or score the versioned SocraticLoop feasibility benchmark.

Default workflow: export blinded prompts, run an open model or coding agent by
an external adapter, then score its JSONL responses. `--provider openai` is an
explicit opt-in API path and reads OPENAI_API_KEY only at execution time.
"""

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

from socratic_loop.feasibility import (
    CONDITIONS,
    decision_from_mapping,
    decision_prompt,
    load_scenarios,
    summarize_scores,
    trajectory_record,
)


def write_jsonl(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")


def parse_json_object(text: str) -> dict:
    match = re.search(r"\{.*\}", text, re.DOTALL)
    if not match:
        raise ValueError("Provider did not return a JSON object.")
    return json.loads(match.group())


def run_openai(scenarios: list[dict], condition: str, model: str) -> list[dict]:
    """Optional provider adapter; no key is read until this path is selected."""
    try:
        from openai import OpenAI
    except ImportError as error:
        raise RuntimeError("Install the optional dependency first: pip install openai") from error
    client = OpenAI()
    outputs = []
    for scenario in scenarios:
        started = time.perf_counter()
        response = client.responses.create(model=model, input=decision_prompt(scenario, condition=condition))
        outputs.append({
            "scenario_id": scenario["id"],
            **parse_json_object(response.output_text),
            "trace": [{
                "type": "openai_response",
                "model": model,
                "latency_ms": round((time.perf_counter() - started) * 1000, 1),
                "response_id": getattr(response, "id", None),
            }],
        })
    return outputs


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--condition", choices=CONDITIONS, required=True)
    parser.add_argument("--write-prompts", type=Path)
    parser.add_argument("--responses", type=Path, help="JSONL responses from an external open model or coding-agent adapter.")
    parser.add_argument("--provider", choices=("openai",))
    parser.add_argument("--model", help="Required with --provider openai.")
    parser.add_argument("--provider-name", default="external_jsonl")
    parser.add_argument("--output", type=Path, default=Path("outputs/feasibility"))
    args = parser.parse_args()

    selected = sum(bool(value) for value in (args.write_prompts, args.responses, args.provider))
    if selected != 1:
        parser.error("select exactly one of --write-prompts, --responses, or --provider")
    if args.provider and not args.model:
        parser.error("--model is required with --provider")

    scenarios = load_scenarios()
    if args.write_prompts:
        rows = [{
            "scenario_id": scenario["id"],
            "condition": args.condition,
            "prompt": decision_prompt(scenario, condition=args.condition),
        } for scenario in scenarios]
        write_jsonl(args.write_prompts, rows)
        print(f"Wrote {len(rows)} blinded prompts to {args.write_prompts}")
        return

    if args.provider == "openai":
        responses = run_openai(scenarios, args.condition, args.model)
        provider_name = f"openai:{args.model}"
    else:
        responses = [json.loads(line) for line in args.responses.read_text(encoding="utf-8").splitlines() if line]
        provider_name = args.provider_name

    by_id = {scenario["id"]: scenario for scenario in scenarios}
    records = []
    for response in responses:
        scenario = by_id[response["scenario_id"]]
        records.append(trajectory_record(
            scenario,
            decision_from_mapping(response),
            condition=args.condition,
            provider_name=provider_name,
            trace=response.get("trace", []),
        ))

    if len(records) != len(scenarios):
        raise ValueError(f"Expected {len(scenarios)} responses, received {len(records)}.")
    args.output.mkdir(parents=True, exist_ok=True)
    write_jsonl(args.output / f"{provider_name.replace(':', '_')}_{args.condition}_trajectories.jsonl", records)
    report = {
        "provider": provider_name,
        "condition": args.condition,
        "provider_decision": summarize_scores(records, score_key="provider_score"),
        "final_decision": summarize_scores(records, score_key="final_score"),
    }
    report_path = args.output / f"{provider_name.replace(':', '_')}_{args.condition}_report.json"
    report_path.write_text(json.dumps(report, indent=2), encoding="utf-8")
    print(json.dumps(report, indent=2))


if __name__ == "__main__":
    main()
