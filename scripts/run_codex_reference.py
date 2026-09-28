"""Run the strong coding-agent reference in isolated benchmark workspaces."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import subprocess
import sys
import time

ROOT = Path(__file__).parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from socratic_loop.agent_benchmark import agent_instructions, load_cases, prepare_workspaces


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--model", default="gpt-5.6-sol")
    parser.add_argument("--workspaces", type=Path, default=Path("outputs/agent_benchmark/workspaces"))
    parser.add_argument("--output", type=Path, default=Path("outputs/agent_benchmark/responses/codex_reference.jsonl"))
    args = parser.parse_args()
    prepare_workspaces(args.workspaces)
    schema = ROOT / "data" / "decision_schema.json"
    raw_root = args.output.parent / "codex_raw"
    raw_root.mkdir(parents=True, exist_ok=True)
    rows = []
    for case in load_cases():
        workspace = (args.workspaces / case["id"]).resolve()
        last_message = raw_root / f"{case['id']}.json"
        command = [
            "codex", "--ask-for-approval", "never", "exec", "--model", args.model,
            "--cd", str(workspace), "--skip-git-repo-check",
            "--sandbox", "workspace-write",
            "--ephemeral", "--output-schema", str(schema.resolve()),
            "--output-last-message", str(last_message.resolve()),
            agent_instructions("codex_reference", workspace),
        ]
        started = time.perf_counter()
        completed = subprocess.run(command, cwd=workspace, capture_output=True, text=True)
        latency_ms = round((time.perf_counter() - started) * 1000, 1)
        if completed.returncode != 0:
            raise RuntimeError(f"Codex failed for {case['id']}: {completed.stderr[-1000:]}")
        decision = json.loads(last_message.read_text(encoding="utf-8"))
        rows.append({"scenario_id": case["id"], **decision, "latency_ms": latency_ms, "model": args.model})
        print(f"Completed {case['id']} in {latency_ms / 1000:.1f}s")
    args.output.parent.mkdir(parents=True, exist_ok=True)
    args.output.write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    print(f"Wrote {len(rows)} responses to {args.output}")


if __name__ == "__main__":
    main()
