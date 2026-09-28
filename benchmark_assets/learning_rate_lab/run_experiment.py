"""Deterministic, dependency-free binary-classification experiment.

The benchmark copies this file into an isolated case workspace. The visible
case configuration controls the optimizer, learning-rate sweep, metric name,
and benchmark-only injected numerical failures. Results are produced by actual
training; injected failures are recorded explicitly in run metadata.
"""

from __future__ import annotations

import json
import math
from pathlib import Path
import random

ROOT = Path(__file__).parent


def load(name: str) -> dict:
    return json.loads((ROOT / name).read_text(encoding="utf-8"))


def dataset(scale: float, seed: int = 7) -> tuple[list[tuple[float, float, int]], list[tuple[float, float, int]]]:
    rng = random.Random(seed)
    rows = []
    for _ in range(160):
        x1 = rng.uniform(-scale, scale)
        x2 = rng.uniform(-scale, scale)
        noise = rng.uniform(-scale / 4, scale / 4)
        label = 1 if 1.4 * x1 - 0.9 * x2 + noise > 0 else 0
        rows.append((x1, x2, label))
    return rows[:120], rows[120:]


def sigmoid(value: float) -> float:
    return 1.0 / (1.0 + math.exp(-max(-30.0, min(30.0, value))))


def evaluate(rows: list[tuple[float, float, int]], weights: list[float], bias: float) -> tuple[float, float]:
    loss = 0.0
    correct = 0
    for x1, x2, label in rows:
        probability = sigmoid(weights[0] * x1 + weights[1] * x2 + bias)
        loss += -(label * math.log(max(probability, 1e-9)) + (1 - label) * math.log(max(1 - probability, 1e-9)))
        correct += int((probability >= 0.5) == bool(label))
    return loss / len(rows), correct / len(rows)


def train(learning_rate: float, optimizer: str, scale: float, epochs: int) -> dict[str, float]:
    train_rows, validation_rows = dataset(scale)
    weights = [0.0, 0.0]
    bias = 0.0
    moments = [0.0, 0.0, 0.0]
    variances = [0.0, 0.0, 0.0]
    step = 0
    for epoch in range(epochs):
        order = list(range(len(train_rows)))
        random.Random(100 + epoch).shuffle(order)
        for index in order:
            x1, x2, label = train_rows[index]
            probability = sigmoid(weights[0] * x1 + weights[1] * x2 + bias)
            gradients = [(probability - label) * x1, (probability - label) * x2, probability - label]
            step += 1
            if optimizer.lower() == "adam":
                updates = []
                for position, gradient in enumerate(gradients):
                    moments[position] = 0.9 * moments[position] + 0.1 * gradient
                    variances[position] = 0.999 * variances[position] + 0.001 * gradient * gradient
                    moment = moments[position] / (1 - 0.9**step)
                    variance = variances[position] / (1 - 0.999**step)
                    updates.append(learning_rate * moment / (math.sqrt(variance) + 1e-8))
            else:
                updates = [learning_rate * gradient for gradient in gradients]
            weights[0] -= updates[0]
            weights[1] -= updates[1]
            bias -= updates[2]
    training_loss, training_accuracy = evaluate(train_rows, weights, bias)
    validation_loss, validation_accuracy = evaluate(validation_rows, weights, bias)
    return {
        "training_loss": round(training_loss, 6),
        "training_accuracy": round(training_accuracy, 6),
        "validation_loss": round(validation_loss, 6),
        "validation_accuracy": round(validation_accuracy, 6),
    }


def main() -> None:
    config = load("actual_config.json")
    contract = load("metric_contract.json")
    injection = load("fault_injection.json")
    observed_name = contract["observed_name"]
    nan_rates = {float(value) for value in injection.get("nan_rates", [])}
    metrics = {}
    full_metrics = {}
    for learning_rate in config["learning_rates"]:
        result = train(float(learning_rate), config["optimizer"], float(config["feature_scale"]), int(config["epochs"]))
        full_metrics[str(learning_rate)] = result
        metrics[str(learning_rate)] = None if float(learning_rate) in nan_rates else result[observed_name]

    artifacts = ROOT / "artifacts"
    artifacts.mkdir(exist_ok=True)
    (artifacts / "metrics.json").write_text(json.dumps({"metric_name": observed_name, "values": metrics}, indent=2), encoding="utf-8")
    (artifacts / "run_metadata.json").write_text(json.dumps({
        "actual_config": config,
        "injected_faults": injection,
        "full_training_metrics": full_metrics,
    }, indent=2), encoding="utf-8")
    print(json.dumps({"metric_name": observed_name, "values": metrics}, indent=2))


if __name__ == "__main__":
    main()
