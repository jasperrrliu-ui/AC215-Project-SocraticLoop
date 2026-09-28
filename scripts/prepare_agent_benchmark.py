from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from socratic_loop.agent_benchmark import SYSTEMS, agent_instructions, prepare_workspaces


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, default=Path("outputs/agent_benchmark/workspaces"))
    args = parser.parse_args()
    manifests = prepare_workspaces(args.output)
    prompt_root = args.output.parent / "prompts"
    prompt_root.mkdir(parents=True, exist_ok=True)
    for system in SYSTEMS:
        rows = [
            {"scenario_id": row["scenario_id"], "workspace": row["workspace"], "prompt": agent_instructions(system, Path(row["workspace"]))}
            for row in manifests
        ]
        (prompt_root / f"{system}.jsonl").write_text("".join(json.dumps(row) + "\n" for row in rows), encoding="utf-8")
    print(f"Prepared {len(manifests)} executable tasks in {args.output}")
    print(f"Exported {len(SYSTEMS)} system prompt sets in {prompt_root}")


if __name__ == "__main__":
    main()
