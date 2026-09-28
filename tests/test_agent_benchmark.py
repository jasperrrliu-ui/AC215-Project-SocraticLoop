import json
from pathlib import Path
import unittest

from socratic_loop.agent_benchmark import (
    HARNESS_SYSTEMS,
    SYSTEMS,
    load_cases,
    model_prompt,
    prepare_workspaces,
    scenario_from_workspace,
)


class AgentBenchmarkTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.root = Path(__file__).parents[1] / "outputs" / "test_agent_benchmark_workspace"
        cls.cases = load_cases()
        prepare_workspaces(cls.root)

    def test_system_matrix_matches_study_design(self):
        self.assertEqual(
            SYSTEMS,
            ("codex_reference", "qwen_raw", "qwen_harness", "qwen_qlora_harness"),
        )
        self.assertEqual(HARNESS_SYSTEMS, {"qwen_harness", "qwen_qlora_harness"})

    def test_eight_executable_cases_cover_four_families(self):
        self.assertEqual(len(self.cases), 8)
        self.assertEqual(
            {case["family"] for case in self.cases},
            {"valid_learning_rate", "configuration_mismatch", "numerical_failure", "metric_contract_mismatch"},
        )

    def test_workspaces_exclude_hidden_oracle_and_execute(self):
        for case in self.cases:
            workspace = self.root / case["id"]
            self.assertTrue((workspace / "run_experiment.py").exists())
            self.assertTrue((workspace / "artifacts" / "metrics.json").exists())
            for file in workspace.rglob("*.json"):
                self.assertNotIn("oracle", file.read_text(encoding="utf-8"))

    def test_real_training_supports_both_valid_oracles(self):
        supporting = next(case for case in self.cases if case["id"] == "exec-valid-high-rate-001")
        refuting = next(case for case in self.cases if case["id"] == "exec-valid-not-cause-001")
        supporting_metrics = scenario_from_workspace(supporting, self.root / supporting["id"])["metrics"]
        refuting_metrics = scenario_from_workspace(refuting, self.root / refuting["id"])["metrics"]
        self.assertGreater(supporting_metrics["0.1"], supporting_metrics["0.01"] * 1.2)
        self.assertEqual(min(refuting_metrics, key=refuting_metrics.get), "0.1")

    def test_harness_prompt_adds_policy_without_oracle(self):
        case = self.cases[4]
        raw = model_prompt("qwen_raw", case, self.root / case["id"])
        harness = model_prompt("qwen_harness", case, self.root / case["id"])
        self.assertNotIn("oracle", raw)
        self.assertNotIn("oracle", harness)
        self.assertNotIn("harness_policy", raw)
        self.assertIn("harness_policy", harness)
        self.assertIn("numerical_failure", harness)

    def test_post_training_builder_is_disjoint_from_frozen_cases(self):
        from scripts.build_post_training_data import record

        frozen_ids = {case["id"] for case in self.cases}
        training = [record(index) for index in range(48)]
        self.assertFalse(frozen_ids & {row["id"] for row in training})
        self.assertTrue(all(row["source"] == "synthetic_train_only" for row in training))
        self.assertEqual(len(training), 48)


if __name__ == "__main__":
    unittest.main()
