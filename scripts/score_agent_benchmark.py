from __future__ import annotations

import argparse
import json
from pathlib import Path
import sys

ROOT = Path(__file__).parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from socratic_loop.agent_benchmark import SYSTEMS, score_system_responses


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--system", choices=SYSTEMS, required=True)
    parser.add_argument("--responses", type=Path, required=True)
    parser.add_argument("--workspaces", type=Path, default=Path("outputs/agent_benchmark/workspaces"))
    parser.add_argument("--output", type=Path, default=Path("outputs/agent_benchmark/reports"))
    args = parser.parse_args()
    responses = [json.loads(line) for line in args.responses.read_text(encoding="utf-8").splitlines() if line]
    if len(responses) != 8:
        raise ValueError(f"Expected 8 responses, received {len(responses)}")
    result = score_system_responses(args.system, responses, args.workspaces)
    args.output.mkdir(parents=True, exist_ok=True)
    (args.output / f"{args.system}_report.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    print(json.dumps(result["summary"], indent=2))


if __name__ == "__main__":
    main()
