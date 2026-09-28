"""Deterministic role implementations with an LLM-replaceable boundary."""


class DeterministicRoleProvider:
    mode = "deterministic_mock_roles"

    def plan(self, state, literature: list[dict]) -> dict:
        return {
            "id": "exp-001",
            "goal": "Test whether a large learning rate is causing unstable validation loss.",
            "hypothesis_ids": ["H1"],
            "planned_config": {"learning_rates": [0.001, 0.01, 0.1], "optimizer": "SGD"},
            "literature_context": [item["id"] for item in literature],
            "rationale": "A learning-rate range can reveal a transition from stable convergence to instability.",
        }

    def checkpoints(self) -> list[dict]:
        return [
            {
                "id": "cp-purpose",
                "kind": "purpose_and_prediction",
                "question": "Which hypothesis does this experiment test, and what do you predict?",
                "answer": "H1: the learning rate is too large; validation loss should become unstable at the largest rate.",
                "status": "answered",
            },
            {
                "id": "cp-interpretation",
                "kind": "interpretation",
                "question": "Does the result support, refute, or fail to determine the hypothesis?",
                "answer": None,
                "status": "pending",
            },
        ]

    def analyze(self, result: dict, validation: dict, literature: list[dict]) -> dict:
        if validation["warnings"]:
            interpretation = "inconclusive"
            conclusion = "The run cannot fairly test H1 because the actual configuration differs from the plan."
        else:
            interpretation = "supports H1"
            conclusion = "The observed instability supports H1."
        return {
            "interpretation": interpretation,
            "conclusion": conclusion,
            "evidence": [
                {"type": "experiment_validation", "claim": warning["message"]}
                for warning in validation["warnings"]
            ] + [
                {"type": "literature", "source": item["id"], "claim": item["claim"]}
                for item in literature
            ],
        }
