"""Run the complete feasibility study across all frozen conditions.

This is the single command used by the Colab notebook. It runs the local
tests first, then evaluates the same eight scenarios under each condition.
The OpenAI provider is opt-in and reads OPENAI_API_KEY from the environment.
"""

from __future__ import annotations

import argparse
import os
import subprocess
import sys
from pathlib import Path

ROOT = Path(__file__).parents[1]
CONDITIONS = (
    "raw_record",
    "validator_augmented",
    "socratic_checkpoint",
    "gated_harness",
)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--provider", choices=("openai",), required=True)
    parser.add_argument("--model", required=True)
    parser.add_argument("--output", type=Path, default=Path("outputs/feasibility"))
    args = parser.parse_args()

    if not os.environ.get("OPENAI_API_KEY"):
        raise SystemExit(
            "OPENAI_API_KEY is not set. Add it to the runtime environment "
            "(for Colab, use a Secret named OPENAI_API_KEY)."
        )

    subprocess.run(
        [sys.executable, "-m", "unittest", "discover", "-s", "tests", "-v"],
        cwd=ROOT,
        check=True,
    )

    for condition in CONDITIONS:
        subprocess.run(
            [
                sys.executable,
                "scripts/run_feasibility.py",
                "--condition",
                condition,
                "--provider",
                args.provider,
                "--model",
                args.model,
                "--output",
                str(args.output),
            ],
            cwd=ROOT,
            check=True,
        )

    print(f"Completed {len(CONDITIONS)} conditions; reports are in {args.output}.")


if __name__ == "__main__":
    main()
