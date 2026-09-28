"""Research-state workflow for the deterministic MVP."""

import json
from dataclasses import asdict
from pathlib import Path

from .contracts import Checkpoint, Hypothesis, ResearchState
from .experiment import execute, validate
from .retrieval import LiteratureRetriever
from .roles import DeterministicRoleProvider


ROOT = Path(__file__).parents[1]


def run_demo() -> dict:
    scenario = json.loads((ROOT / "data" / "scenarios.json").read_text(encoding="utf-8"))[0]
    state = ResearchState(
        question=scenario["question"],
        hypotheses=[Hypothesis(**item) for item in scenario["hypotheses"]],
    )
    retriever = LiteratureRetriever(ROOT / "data" / "literature.json")
    roles = DeterministicRoleProvider()

    literature = retriever.search(state.question + " learning rate instability model capacity")
    state.experiment = roles.plan(state, literature)
    state.checkpoints = [Checkpoint(**item) for item in roles.checkpoints()]
    result = execute(state.experiment)
    validation = validate(result)
    analysis = roles.analyze(result, validation, literature)
    state.checkpoints[-1].answer = analysis["interpretation"]
    state.checkpoints[-1].status = "answered"
    state.evidence = analysis["evidence"]
    state.conclusion = analysis["conclusion"]

    return {
        "scenario": scenario["name"],
        "mode": roles.mode,
        "literature": literature,
        "research_state": asdict(state),
        "run": result,
        "validation": validation,
        "analysis": analysis,
    }
