import copy
import importlib.util
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

import yaml

ROOT = Path(__file__).resolve().parents[1]
sys.path[:0] = [str(ROOT / "runtime"), str(ROOT)]
spec = importlib.util.spec_from_file_location("lab_setup", ROOT / "runtime/setup.py")
setup = importlib.util.module_from_spec(spec)
spec.loader.exec_module(setup)
from package import policy


class KitChecks(unittest.TestCase):
    def setUp(self):
        self.config = {"PlatformName": "fidelity-india", "StudentCount": "143", "ClusterName": "fidelity-india",
                       "GitHubOrganisation": "training", "JenkinsSecretArn": "jenkins"}
        self.event = {"ResourceType": "Custom::FidelityLearner", "LogicalResourceId": "EnvironmentSetup",
                      "RequestType": "Create", "StackId": "arn:aws:cloudformation:ap-south-1:123456789012:stack/s001/uuid",
                      "ResourceProperties": {"EnvironmentId": "s001", "PlatformName": "fidelity-india",
                         "Namespace": "etp-s001", "ClusterName": "fidelity-india",
                         "GitHubRepository": "https://github.com/training/team-1", "GitHubBranch": "main"}}

    def test_student_cannot_claim_another_id_or_unapproved_repository(self):
        self.assertEqual(setup.validate(self.event, self.config), "s001")
        for key, value in [("EnvironmentId", "s002"), ("Namespace", "etp-s002"),
                           ("GitHubRepository", "https://github.com/unapproved/repo")]:
            event = copy.deepcopy(self.event)
            event["ResourceProperties"][key] = value
            with self.assertRaises(ValueError):
                setup.validate(event, self.config)

    def test_route_assignments_fit_all_students_without_collisions(self):
        template = yaml.safe_load((ROOT / "learner.yaml").read_text())
        assignments = template["Mappings"]["Students"]
        self.assertEqual(len(assignments), 143)
        pairs = {(v["Alb"], v["Slot"]) for v in assignments.values()}
        self.assertEqual(len(pairs), 143)
        self.assertTrue(all(1 <= slot <= 30 for _, slot in pairs))

    def test_failed_build_stop_prevents_data_deletion(self):
        with patch.object(setup, "read_secret", return_value={}), patch.object(setup, "jenkins", return_value=Mock()), \
             patch.object(setup, "stop_job"), patch.object(setup, "stop_builds", side_effect=RuntimeError("still running")), \
             patch.object(setup, "connect_cluster") as cluster, patch.object(setup, "empty_bucket") as bucket:
            with self.assertRaises(RuntimeError):
                setup.remove_environment(self.event, self.config, "s001")
            cluster.assert_not_called()
            bucket.assert_not_called()

    def test_learner_policy_requires_assigned_stack_template_and_role(self):
        permissions = policy("123456789012", "ap-south-1", "fidelity-india", "s001", "https://approved/learner.yaml", "arn:role/lab")
        create = permissions["Statement"][0]
        self.assertTrue(create["Resource"].endswith(":stack/s001/*"))
        self.assertEqual(create["Condition"]["StringEquals"], {
            "cloudformation:TemplateUrl": "https://approved/learner.yaml", "cloudformation:RoleARN": "arn:role/lab"})


if __name__ == "__main__":
    unittest.main()
