import unittest

from socratic_loop.workflow import run_demo


class WorkflowTests(unittest.TestCase):
    def test_demo_has_retrieval_checkpoints_and_grounded_warning(self):
        result = run_demo()
        self.assertEqual(result["mode"], "deterministic_mock_roles")
        self.assertTrue(result["literature"])
        self.assertEqual(len(result["research_state"]["checkpoints"]), 2)
        self.assertEqual(result["validation"]["status"], "warning")
        self.assertEqual(result["analysis"]["interpretation"], "inconclusive")
        self.assertIn("configuration_mismatch", str(result["validation"]))


if __name__ == "__main__":
    unittest.main()
