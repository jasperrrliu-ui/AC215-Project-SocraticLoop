"""Research-state workflow with a pause/resume conversational boundary."""

import json
import uuid
from dataclasses import asdict
from pathlib import Path

from .contracts import Checkpoint, Hypothesis, ResearchState
from .experiment import execute, validate
from .retrieval import LiteratureRetriever
from .roles import DeterministicRoleProvider

ROOT = Path(__file__).parents[1]


class DemoSession:
    """In-memory session for the first local demo; replace with SQLite later."""

    def __init__(self, question: str | None = None):
        scenario = json.loads((ROOT / "data" / "scenarios.json").read_text(encoding="utf-8"))[0]
        self.id = f"session-{uuid.uuid4().hex[:8]}"
        self.scenario = scenario
        self.roles = DeterministicRoleProvider()
        self.retriever = LiteratureRetriever(ROOT / "data" / "literature.json")
        self.state = ResearchState(
            question=question or scenario["question"],
            hypotheses=[Hypothesis(**item) for item in scenario["hypotheses"]],
        )
        self.literature = self.retriever.search(self.state.question + " learning rate instability model capacity")
        self.result = None
        self.validation = None
        self.analysis = None
        self.phase = "planning"

    def start(self) -> dict:
        self.state.experiment = self.roles.plan(self.state, self.literature)
        self.state.checkpoints = [Checkpoint(**item) for item in self.roles.checkpoints()]
        self.phase = "purpose_and_prediction"
        return self.snapshot()

    def answer(self, checkpoint_id: str, answer: str) -> dict:
        checkpoint = next((item for item in self.state.checkpoints if item.id == checkpoint_id), None)
        if checkpoint is None:
            raise KeyError(f"Unknown checkpoint: {checkpoint_id}")
        checkpoint.answer = answer
        checkpoint.status = "answered"
        if checkpoint.kind == "purpose_and_prediction":
            self.result = execute(self.state.experiment)
            self.validation = validate(self.result)
            self.phase = "interpretation"
        elif checkpoint.kind == "interpretation":
            self.analysis = self.roles.analyze(self.result, self.validation, self.literature)
            self.state.evidence = self.analysis["evidence"]
            self.state.conclusion = self.analysis["conclusion"]
            self.phase = "completed"
        return self.snapshot()

    def snapshot(self) -> dict:
        return {
            "session_id": self.id,
            "mode": self.roles.mode,
            "phase": self.phase,
            "literature": self.literature,
            "research_state": asdict(self.state),
            "run": self.result,
            "validation": self.validation,
            "analysis": self.analysis,
        }


def run_demo() -> dict:
    """Run the complete deterministic path for tests and compatibility."""
    session = DemoSession()
    session.start()
    session.answer("cp-purpose", "H1; validation loss should become unstable at the largest rate.")
    return session.answer("cp-interpretation", "Inconclusive because the actual configuration differs from the plan.")
