"""Executable benchmark contract for comparing complete agent systems."""

from __future__ import annotations

import json
from pathlib import Path
import shutil
import subprocess
import sys
from typing import Any

from .feasibility import Decision, score_decision, validator_events

ROOT = Path(__file__).parents[1]
SYSTEMS = (
    "codex_reference",
    "qwen_raw",
    "qwen_harness",
    "qwen_qlora_harness",
)
HARNESS_SYSTEMS = {"qwen_harness", "qwen_qlora_harness"}


def load_cases(path: Path | None = None) -> list[dict[str, Any]]:
    source = path or ROOT / "data" / "agent_benchmark_cases.json"
    return json.loads(source.read_text(encoding="utf-8"))


def visible_case(case: dict[str, Any]) -> dict[str, Any]:
    return {key: value for key, value in case.items() if key != "oracle"}


def prepare_workspaces(destination: Path, *, execute: bool = True) -> list[dict[str, Any]]:
    """Create isolated task directories that never contain hidden oracles."""
    template = ROOT / "benchmark_assets" / "learning_rate_lab" / "run_experiment.py"
    manifests = []
    for case in load_cases():
        workspace = destination / case["id"]
        workspace.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(template, workspace / "run_experiment.py")
        profile = case["profile"]
        actual_config = {
            **case["actual_config"],
            "feature_scale": profile["feature_scale"],
            "epochs": profile["epochs"],
        }
        files = {
            "task.json": {
                "scenario_id": case["id"],
                "question": "Does an excessively high learning rate explain the validation-loss behavior?",
                "target_hypothesis": {"id": "H1", "text": "The learning rate is too large."},
                "alternative_hypothesis": {"id": "H2", "text": "Model capacity is insufficient."},
            },
            "planned_config.json": case["planned_config"],
            "actual_config.json": actual_config,
            "metric_contract.json": case["metric_contract"],
            "fault_injection.json": case["fault_injection"],
            "researcher_checkpoint.json": case["researcher_checkpoint"],
        }
        for name, payload in files.items():
            (workspace / name).write_text(json.dumps(payload, indent=2), encoding="utf-8")
        if execute:
            subprocess.run([sys.executable, "run_experiment.py"], cwd=workspace, check=True, capture_output=True, text=True)
        manifests.append({"scenario_id": case["id"], "workspace": str(workspace.resolve())})
    return manifests


def scenario_from_workspace(case: dict[str, Any], workspace: Path) -> dict[str, Any]:
    task = json.loads((workspace / "task.json").read_text(encoding="utf-8"))
    metrics_artifact = json.loads((workspace / "artifacts" / "metrics.json").read_text(encoding="utf-8"))
    actual = json.loads((workspace / "actual_config.json").read_text(encoding="utf-8"))
    planned = json.loads((workspace / "planned_config.json").read_text(encoding="utf-8"))
    comparable_actual = {key: actual[key] for key in ("learning_rates", "optimizer")}
    return {
        "id": case["id"],
        "family": case["family"],
        "question": task["question"],
        "target_hypothesis": task["target_hypothesis"],
        "alternative_hypothesis": task["alternative_hypothesis"],
        "planned_config": planned,
        "actual_config": comparable_actual,
        "metric_contract": json.loads((workspace / "metric_contract.json").read_text(encoding="utf-8")),
        "metrics": metrics_artifact["values"],
        "researcher_checkpoint": json.loads((workspace / "researcher_checkpoint.json").read_text(encoding="utf-8")),
        "oracle": case["oracle"],
    }


def agent_instructions(system: str, workspace: Path) -> str:
    if system not in SYSTEMS:
        raise ValueError(f"Unknown system: {system}")
    harness = ""
    if system in HARNESS_SYSTEMS:
        harness = (
            "Before deciding, compare planned_config.json with actual_config.json; validate numerical outputs and "
            "the metric contract; use researcher_checkpoint.json; never update a hypothesis from invalid evidence. "
        )
    return (
        f"Work only in {workspace}. Run python run_experiment.py if artifacts are absent. "
        "Inspect the visible files and return exactly one JSON object with detected_faults, evidence_status, "
        "hypothesis_status, next_action_code, and rationale. " + harness
    )


def model_prompt(system: str, case: dict[str, Any], workspace: Path) -> str:
    """Build the blinded artifact bundle used by the small-model systems."""
    if system not in {"qwen_raw", "qwen_harness", "qwen_qlora_harness"}:
        raise ValueError(f"Model prompt is not defined for {system}")
    scenario = scenario_from_workspace(case, workspace)
    visible = {key: value for key, value in scenario.items() if key != "oracle"}
    if system in HARNESS_SYSTEMS:
        visible["validator_events"] = validator_events(scenario)
        visible["harness_policy"] = "Invalid evidence must leave the hypothesis unresolved and select the matching rerun action."
    else:
        visible.pop("researcher_checkpoint", None)
    return (
        "Diagnose this executed machine-learning experiment. Return one JSON object and no markdown. "
        "Required keys: detected_faults (array using only configuration_mismatch, numerical_failure, "
        "metric_contract_mismatch), evidence_status (valid or invalid), hypothesis_status "
        "(supported, refuted, or unresolved), next_action_code, and rationale. Allowed next actions: "
        "run_narrower_learning_rate_sweep, increase_model_capacity, rerun_with_planned_config, "
        "rerun_with_lower_learning_rate, rerun_with_validation_metric, inspect_data_pipeline.\n\n"
        + json.dumps(visible, indent=2)
    )


def score_system_responses(system: str, responses: list[dict[str, Any]], workspace_root: Path) -> dict[str, Any]:
    by_id = {row["scenario_id"]: row for row in responses}
    records = []
    for case in load_cases():
        response = by_id[case["id"]]
        decision = Decision(
            tuple(response.get("detected_faults", [])),
            response.get("evidence_status", ""),
            response.get("hypothesis_status", ""),
            response.get("next_action_code", ""),
            response.get("rationale", ""),
        )
        scenario = scenario_from_workspace(case, workspace_root / case["id"])
        score = score_decision(scenario, decision)
        records.append({
            "scenario_id": case["id"],
            "system": system,
            "decision": response,
            "score": score,
            "validator_events": validator_events(scenario),
            "latency_ms": response.get("latency_ms"),
            "tool_calls": response.get("tool_calls"),
            "input_tokens": response.get("input_tokens"),
            "output_tokens": response.get("output_tokens"),
            "estimated_cost_usd": response.get("estimated_cost_usd"),
        })
    total = len(records)
    checks = ("schema_compliant", "evidence_status_correct", "hypothesis_status_correct", "next_action_correct")
    summary = {key: sum(int(row["score"][key]) for row in records) / total for key in checks}
    summary.update({
        "system": system,
        "scenarios": total,
        "fault_precision": sum(row["score"]["fault_precision"] for row in records) / total,
        "fault_recall": sum(row["score"]["fault_recall"] for row in records) / total,
        "unsafe_hypothesis_updates": sum(int(row["score"]["unsafe_hypothesis_update"]) for row in records),
        "reported_cost_usd": sum(row["estimated_cost_usd"] or 0 for row in records),
    })
    return {"summary": summary, "records": records}
