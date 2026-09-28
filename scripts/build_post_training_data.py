"""Build a disjoint synthetic SFT set for the lightweight QLoRA pilot."""

from __future__ import annotations

import json
from pathlib import Path
import random
import sys

ROOT = Path(__file__).parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from socratic_loop.feasibility import ACTION_CODES

OUTPUT = Path("outputs/post_training")


def record(index: int) -> dict:
    rng = random.Random(9000 + index)
    family = index % 6
    rates = [round(0.0004 + index * 0.00001, 6), round(0.004 + index * 0.00003, 6), round(0.04 + index * 0.0002, 6)]
    planned = {"learning_rates": rates, "optimizer": "SGD"}
    actual = dict(planned)
    expected = observed = "validation_loss"
    metrics = {str(rates[0]): round(rng.uniform(0.7, 1.0), 4), str(rates[1]): round(rng.uniform(0.3, 0.6), 4), str(rates[2]): round(rng.uniform(1.1, 1.8), 4)}
    faults = []
    evidence, hypothesis, action = "valid", "supported", "run_narrower_learning_rate_sweep"
    if family == 1:
        metrics[str(rates[2])] = round(rng.uniform(0.15, 0.25), 4)
        hypothesis, action = "refuted", "increase_model_capacity"
    elif family == 2:
        actual = {"learning_rates": [rates[0], rates[2], round(rates[2] * 10, 6)], "optimizer": "SGD"}
        faults, evidence, hypothesis, action = ["configuration_mismatch"], "invalid", "unresolved", "rerun_with_planned_config"
    elif family == 3:
        actual = {"learning_rates": rates, "optimizer": "Adam"}
        faults, evidence, hypothesis, action = ["configuration_mismatch"], "invalid", "unresolved", "rerun_with_planned_config"
    elif family == 4:
        metrics[str(rates[2])] = None
        faults, evidence, hypothesis, action = ["numerical_failure"], "invalid", "unresolved", "rerun_with_lower_learning_rate"
    elif family == 5:
        observed = "training_loss" if index % 2 else "validation_accuracy"
        faults, evidence, hypothesis, action = ["metric_contract_mismatch"], "invalid", "unresolved", "rerun_with_validation_metric"
    visible = {
        "scenario_id": f"train-only-{index:03d}",
        "question": "Does a high learning rate explain the validation behavior?",
        "target_hypothesis": {"id": "H1", "text": "The learning rate is too large."},
        "planned_config": planned,
        "actual_config": actual,
        "metric_contract": {"expected_name": expected, "observed_name": observed},
        "metrics": metrics,
        "researcher_checkpoint": {"purpose": "Test learning-rate stability.", "prediction": "Invalid evidence cannot update H1."},
    }
    answer = {
        "detected_faults": faults,
        "evidence_status": evidence,
        "hypothesis_status": hypothesis,
        "next_action_code": action,
        "rationale": "Decision follows the configuration, numerical, and metric validity contract.",
    }
    assert action in ACTION_CODES
    return {"id": visible["scenario_id"], "source": "synthetic_train_only", "input": visible, "output": answer}


def main() -> None:
    rows = [record(index) for index in range(48)]
    OUTPUT.mkdir(parents=True, exist_ok=True)
    for name, subset in (("train", rows[:40]), ("validation", rows[40:])):
        (OUTPUT / f"{name}.jsonl").write_text("".join(json.dumps(row) + "\n" for row in subset), encoding="utf-8")
    print("Wrote 40 train and 8 validation records; frozen benchmark cases were not used.")


if __name__ == "__main__":
    main()
