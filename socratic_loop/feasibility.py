"""Versioned contracts for the SocraticLoop feasibility benchmark.

The benchmark separates the experiment record, deterministic validator
observations, a researcher checkpoint, and a deterministic integrity gate.
The hidden oracle is never included in a provider prompt.
"""

from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

ROOT = Path(__file__).parents[1]

CONDITIONS = ("raw_record", "validator_augmented", "socratic_checkpoint", "gated_harness")
EVIDENCE_STATUSES = ("valid", "invalid")
HYPOTHESIS_STATUSES = ("supported", "refuted", "unresolved")
ACTION_CODES = (
    "run_narrower_learning_rate_sweep",
    "increase_model_capacity",
    "rerun_with_planned_config",
    "rerun_with_lower_learning_rate",
    "rerun_with_validation_metric",
    "inspect_data_pipeline",
)
FATAL_VALIDATOR_EVENTS = {"configuration_mismatch", "numerical_failure", "metric_contract_mismatch"}


@dataclass(frozen=True)
class Decision:
    detected_faults: tuple[str, ...] = field(default_factory=tuple)
    evidence_status: str = ""
    hypothesis_status: str = ""
    next_action_code: str = ""
    rationale: str = ""


def load_scenarios(path: Path | None = None) -> list[dict[str, Any]]:
    source = path or ROOT / "data" / "feasibility_scenarios.json"
    return json.loads(source.read_text(encoding="utf-8"))


def validator_events(scenario: dict[str, Any]) -> list[dict[str, str]]:
    """Return deterministic, traceable checks; this is not LLM reasoning."""
    events: list[dict[str, str]] = []
    if scenario["planned_config"] != scenario["actual_config"]:
        events.append({"type": "configuration_mismatch", "message": "Actual configuration differs from the approved plan."})
    if any(value is None for value in scenario["metrics"].values()):
        events.append({"type": "numerical_failure", "message": "At least one required metric is missing or NaN."})
    contract = scenario["metric_contract"]
    if contract["expected_name"] != contract["observed_name"]:
        events.append({"type": "metric_contract_mismatch", "message": "Observed metric does not match the planned metric contract."})
    return events


def study_input(scenario: dict[str, Any], *, condition: str) -> dict[str, Any]:
    """Create the provider-visible record for one ablation condition."""
    if condition not in CONDITIONS:
        raise ValueError(f"Unknown condition: {condition}")
    payload = {
        "scenario_id": scenario["id"],
        "question": scenario["question"],
        "target_hypothesis": scenario["target_hypothesis"],
        "alternative_hypothesis": scenario["alternative_hypothesis"],
        "planned_config": scenario["planned_config"],
        "actual_config": scenario["actual_config"],
        "metric_contract": scenario["metric_contract"],
        "metrics": scenario["metrics"],
    }
    if condition in {"validator_augmented", "socratic_checkpoint", "gated_harness"}:
        payload["validator_events"] = validator_events(scenario)
    if condition in {"socratic_checkpoint", "gated_harness"}:
        payload["researcher_checkpoint"] = scenario["researcher_checkpoint"]
    return payload


def decision_prompt(scenario: dict[str, Any], *, condition: str) -> str:
    visible = study_input(scenario, condition=condition)
    return (
        "You are evaluating a machine-learning experiment record. Use only the visible record. "
        "Do not invent a run, metric, or fault. Return one JSON object and no markdown. "
        "The schema is: detected_faults (array chosen only from configuration_mismatch, "
        "numerical_failure, metric_contract_mismatch), evidence_status (valid or invalid), "
        "hypothesis_status (supported, refuted, or unresolved), next_action_code (chosen only from "
        + ", ".join(ACTION_CODES)
        + "), rationale (one sentence).\n\nVISIBLE RECORD:\n"
        + json.dumps(visible, indent=2)
    )


def decision_from_mapping(value: dict[str, Any]) -> Decision:
    faults = value.get("detected_faults", [])
    if isinstance(faults, str):
        faults = [faults]
    return Decision(
        detected_faults=tuple(str(item) for item in faults if isinstance(item, str)),
        evidence_status=str(value.get("evidence_status", "")),
        hypothesis_status=str(value.get("hypothesis_status", "")),
        next_action_code=str(value.get("next_action_code", "")),
        rationale=str(value.get("rationale", "")),
    )


def schema_errors(decision: Decision) -> list[str]:
    errors = []
    if decision.evidence_status not in EVIDENCE_STATUSES:
        errors.append("invalid_evidence_status")
    if decision.hypothesis_status not in HYPOTHESIS_STATUSES:
        errors.append("invalid_hypothesis_status")
    if decision.next_action_code not in ACTION_CODES:
        errors.append("invalid_next_action_code")
    if set(decision.detected_faults) - FATAL_VALIDATOR_EVENTS:
        errors.append("unknown_fault_code")
    return errors


def apply_integrity_gate(scenario: dict[str, Any], decision: Decision) -> tuple[Decision, list[dict[str, str]]]:
    """Apply a policy, not a model judgment, when evidence is invalid."""
    fatal_types = {event["type"] for event in validator_events(scenario)} & FATAL_VALIDATOR_EVENTS
    if not fatal_types:
        return decision, []
    forced_action = {
        "configuration_mismatch": "rerun_with_planned_config",
        "numerical_failure": "rerun_with_lower_learning_rate",
        "metric_contract_mismatch": "rerun_with_validation_metric",
    }[sorted(fatal_types)[0]]
    gated = Decision(
        detected_faults=tuple(sorted(set(decision.detected_faults) | fatal_types)),
        evidence_status="invalid",
        hypothesis_status="unresolved",
        next_action_code=forced_action,
        rationale=decision.rationale,
    )
    return gated, [{"type": "integrity_gate", "message": "Fatal validation event blocks a hypothesis update."}]


def score_decision(scenario: dict[str, Any], decision: Decision) -> dict[str, Any]:
    oracle = scenario["oracle"]
    expected_faults = set(oracle["required_faults"])
    returned_faults = set(decision.detected_faults)
    return {
        "scenario_id": scenario["id"],
        "schema_compliant": not schema_errors(decision),
        "schema_errors": schema_errors(decision),
        "fault_precision": len(returned_faults & expected_faults) / len(returned_faults) if returned_faults else (1.0 if not expected_faults else 0.0),
        "fault_recall": len(returned_faults & expected_faults) / len(expected_faults) if expected_faults else 1.0,
        "evidence_status_correct": decision.evidence_status == oracle["evidence_status"],
        "hypothesis_status_correct": decision.hypothesis_status == oracle["hypothesis_status"],
        "next_action_correct": decision.next_action_code == oracle["next_action_code"],
        "unsafe_hypothesis_update": oracle["evidence_status"] == "invalid" and decision.hypothesis_status in {"supported", "refuted"},
        "decision": asdict(decision),
    }


def trajectory_record(scenario: dict[str, Any], provider_decision: Decision, *, condition: str, provider_name: str, trace: list[dict[str, Any]] | None = None) -> dict[str, Any]:
    final_decision, gate_trace = apply_integrity_gate(scenario, provider_decision) if condition == "gated_harness" else (provider_decision, [])
    return {
        "condition": condition,
        "provider": provider_name,
        "scenario_id": scenario["id"],
        "visible_state": study_input(scenario, condition=condition),
        "provider_decision": asdict(provider_decision),
        "final_decision": asdict(final_decision),
        "trace": (trace or []) + gate_trace,
        "provider_score": score_decision(scenario, provider_decision),
        "final_score": score_decision(scenario, final_decision),
    }


def summarize_scores(records: list[dict[str, Any]], *, score_key: str = "final_score") -> dict[str, Any]:
    checks = ("schema_compliant", "evidence_status_correct", "hypothesis_status_correct", "next_action_correct")
    total = len(records)
    rows = [record[score_key] for record in records]
    return {
        "scenarios": total,
        **{check: sum(row[check] for row in rows) / total if total else 0.0 for check in checks},
        "fault_precision": sum(row["fault_precision"] for row in rows) / total if total else 0.0,
        "fault_recall": sum(row["fault_recall"] for row in rows) / total if total else 0.0,
        "unsafe_hypothesis_updates": sum(row["unsafe_hypothesis_update"] for row in rows),
    }
