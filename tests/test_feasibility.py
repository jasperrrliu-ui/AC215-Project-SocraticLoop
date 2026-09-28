import unittest

from socratic_loop.feasibility import (
    CONDITIONS,
    Decision,
    apply_integrity_gate,
    decision_prompt,
    load_scenarios,
    schema_errors,
    score_decision,
    study_input,
    summarize_scores,
    trajectory_record,
    validator_events,
)


class FeasibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.scenarios = load_scenarios()

    def scenario(self, scenario_id):
        return next(item for item in self.scenarios if item["id"] == scenario_id)

    def test_eight_versioned_cases_cover_four_families(self):
        self.assertEqual(len(self.scenarios), 8)
        self.assertEqual(
            {item["family"] for item in self.scenarios},
            {"valid_learning_rate", "configuration_mismatch", "numerical_failure", "metric_contract_mismatch"},
        )

    def test_oracle_is_hidden_in_all_provider_conditions(self):
        scenario = self.scenario("lr-config-sweep-mismatch-001")
        for condition in CONDITIONS:
            payload = study_input(scenario, condition=condition)
            prompt = decision_prompt(scenario, condition=condition)
            self.assertNotIn("oracle", payload)
            self.assertNotIn("oracle", prompt)

    def test_condition_ablation_is_explicit(self):
        scenario = self.scenario("lr-numerical-high-rate-001")
        raw = study_input(scenario, condition="raw_record")
        validated = study_input(scenario, condition="validator_augmented")
        checkpointed = study_input(scenario, condition="socratic_checkpoint")
        self.assertNotIn("validator_events", raw)
        self.assertEqual({item["type"] for item in validated["validator_events"]}, {"numerical_failure"})
        self.assertIn("researcher_checkpoint", checkpointed)

    def test_validator_has_distinct_fault_taxonomy(self):
        config = self.scenario("lr-config-optimizer-mismatch-001")
        metric = self.scenario("lr-metric-train-loss-001")
        self.assertEqual({item["type"] for item in validator_events(config)}, {"configuration_mismatch"})
        self.assertEqual({item["type"] for item in validator_events(metric)}, {"metric_contract_mismatch"})

    def test_schema_rejects_free_text_action_and_invalid_enum(self):
        decision = Decision(("numerical_failure",), "supported", "unresolved", "rerun soon", "bad enum")
        self.assertEqual(set(schema_errors(decision)), {"invalid_evidence_status", "invalid_next_action_code"})

    def test_invalid_evidence_policy_rejects_model_conclusion(self):
        scenario = self.scenario("lr-numerical-high-rate-001")
        decision = Decision(("numerical_failure",), "invalid", "supported", "rerun_with_lower_learning_rate", "NaN supports H1")
        score = score_decision(scenario, decision)
        self.assertTrue(score["unsafe_hypothesis_update"])
        self.assertFalse(score["hypothesis_status_correct"])

    def test_gate_is_policy_and_preserves_provider_decision(self):
        scenario = self.scenario("lr-config-sweep-mismatch-001")
        provider = Decision((), "valid", "supported", "increase_model_capacity", "wrong conclusion")
        record = trajectory_record(scenario, provider, condition="gated_harness", provider_name="test")
        self.assertEqual(record["provider_decision"]["hypothesis_status"], "supported")
        self.assertEqual(record["final_decision"]["evidence_status"], "invalid")
        self.assertEqual(record["final_decision"]["hypothesis_status"], "unresolved")
        self.assertEqual(record["final_decision"]["next_action_code"], "rerun_with_planned_config")
        self.assertEqual(record["trace"][-1]["type"], "integrity_gate")

    def test_clean_case_is_not_changed_by_gate(self):
        scenario = self.scenario("lr-valid-high-rate-001")
        decision = Decision((), "valid", "supported", "run_narrower_learning_rate_sweep", "expected pattern")
        gated, trace = apply_integrity_gate(scenario, decision)
        self.assertEqual(gated, decision)
        self.assertEqual(trace, [])

    def test_summary_reports_provider_and_final_safely(self):
        scenario = self.scenario("lr-numerical-high-rate-001")
        record = trajectory_record(
            scenario,
            Decision(("numerical_failure",), "invalid", "supported", "rerun_with_lower_learning_rate", "wrong update"),
            condition="gated_harness",
            provider_name="test",
        )
        self.assertEqual(summarize_scores([record], score_key="provider_score")["unsafe_hypothesis_updates"], 1)
        self.assertEqual(summarize_scores([record], score_key="final_score")["unsafe_hypothesis_updates"], 0)
