"""Deterministic synthetic experiment executor and validator."""


def execute(plan: dict) -> dict:
    # Controlled fault: the actual run silently uses a different sweep.
    return {
        "run_id": "run-001",
        "planned_config": plan["planned_config"],
        "actual_config": {"learning_rates": [0.001, 0.1, 1.0], "optimizer": "SGD"},
        "metrics": {"0.001": 0.94, "0.1": 0.71, "1.0": None},
        "plot": "synthetic_validation_loss_curve",
    }


def validate(result: dict) -> dict:
    warnings = []
    if result["planned_config"] != result["actual_config"]:
        warnings.append({
            "type": "configuration_mismatch",
            "message": "Actual learning-rate sweep does not match the planned sweep.",
        })
    if any(value is None for value in result["metrics"].values()):
        warnings.append({
            "type": "numerical_failure",
            "message": "The highest learning rate produced a missing metric.",
        })
    return {"status": "warning" if warnings else "ok", "warnings": warnings}
