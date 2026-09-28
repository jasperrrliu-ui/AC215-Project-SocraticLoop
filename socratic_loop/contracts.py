"""Small typed contracts for the first SocraticLoop vertical slice."""

from dataclasses import dataclass, field


@dataclass
class Hypothesis:
    id: str
    text: str
    status: str = "open"


@dataclass
class Checkpoint:
    id: str
    kind: str
    question: str
    answer: str | None = None
    status: str = "pending"


@dataclass
class ResearchState:
    question: str
    hypotheses: list[Hypothesis]
    experiment: dict | None = None
    checkpoints: list[Checkpoint] = field(default_factory=list)
    evidence: list[dict] = field(default_factory=list)
    conclusion: str | None = None
