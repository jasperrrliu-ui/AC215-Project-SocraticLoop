import unittest

from socratic_loop.workflow import DemoSession, run_demo


class WorkflowTests(unittest.TestCase):
    def test_demo_has_retrieval_checkpoints_and_grounded_warning(self):
        result = run_demo()
        self.assertEqual(result["mode"], "deterministic_mock_roles")
        self.assertTrue(result["literature"])
        self.assertEqual(len(result["research_state"]["checkpoints"]), 2)
        self.assertEqual(result["validation"]["status"], "warning")
        self.assertEqual(result["analysis"]["interpretation"], "inconclusive")
        self.assertIn("configuration_mismatch", str(result["validation"]))

    def test_session_pauses_then_resumes_at_checkpoint(self):
        session = DemoSession()
        first = session.start()
        self.assertEqual(first["phase"], "purpose_and_prediction")
        self.assertEqual(first["research_state"]["checkpoints"][1]["status"], "pending")
        second = session.answer("cp-purpose", "H1; the largest learning rate will be unstable.")
        self.assertEqual(second["phase"], "interpretation")
        self.assertIsNotNone(second["validation"])
        final = session.answer("cp-interpretation", "Inconclusive because the configuration changed.")
        self.assertEqual(final["phase"], "completed")
        self.assertIn("cannot fairly test", final["research_state"]["conclusion"])


if __name__ == "__main__":
    unittest.main()
