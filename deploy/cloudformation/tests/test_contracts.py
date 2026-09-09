"""Check isolation and deployment contracts without connecting to an AWS account."""

import ast
import base64
from pathlib import Path
import re
import sys
import unittest

from cfnlint.decode import decode

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from environment import application_secret, namespace_documents  # noqa: E402
from bootstrap_platform import platform_documents  # noqa: E402
from release import release_values  # noqa: E402


def settings(env):
    return {"Namespace": f"etp-{env}", "EnvironmentId": env,
            "FrontendUrl": f"https://{env}.cloudfront.net",
            "ApiTargetGroupArn": f"arn:aws:elasticloadbalancing:ap-south-1:123456789012:targetgroup/{env}-api/123",
            "AuthTargetGroupArn": f"arn:aws:elasticloadbalancing:ap-south-1:123456789012:targetgroup/{env}-auth/123",
            "AnalyticsTargetGroupArn": f"arn:aws:elasticloadbalancing:ap-south-1:123456789012:targetgroup/{env}-analytics/123"}


SHARED = {"VpcId": "vpc-example", "VpcCidr": "10.80.0.0/16",
          "PublicSubnetCidrA": "10.80.0.0/24", "PublicSubnetCidrB": "10.80.1.0/24"}


class DeploymentContracts(unittest.TestCase):
    def test_groups_get_separate_namespaces_and_target_bindings(self):
        groups = [namespace_documents(SHARED, settings(env)) for env in ("g001", "g002")]
        for documents, env in zip(groups, ("g001", "g002")):
            for document in documents:
                if document["kind"] != "Namespace":
                    self.assertEqual(document["metadata"]["namespace"], f"etp-{env}")
            targets = [d for d in documents if d["kind"] == "TargetGroupBinding"]
            self.assertEqual(len(targets), 3)
            self.assertTrue(all(f"/{env}-" in d["spec"]["targetGroupARN"] for d in targets))

    def test_release_role_cannot_change_isolation_or_public_routing(self):
        documents = namespace_documents(SHARED, settings("g001"))
        role = next(d for d in documents if d["kind"] == "Role")
        resources = {r for rule in role["rules"] for r in rule["resources"]}
        forbidden = {"*", "roles", "rolebindings", "networkpolicies", "namespaces", "targetgroupbindings", "ingresses", "resourcequotas"}
        self.assertFalse(resources & forbidden)
        for rule in role["rules"]:
            if "persistentvolumeclaims" in rule["resources"]:
                self.assertNotIn("delete", rule["verbs"])

    def test_namespace_blocks_public_services_and_privileged_pods(self):
        documents = namespace_documents(SHARED, settings("g001"))
        namespace = documents[0]
        self.assertEqual(namespace["metadata"]["labels"]["pod-security.kubernetes.io/enforce"], "restricted")
        quota = next(d for d in documents if d["kind"] == "ResourceQuota")
        self.assertEqual(quota["spec"]["hard"]["services.loadbalancers"], "0")
        self.assertEqual(quota["spec"]["hard"]["services.nodeports"], "0")
        policy = next(d for d in platform_documents("lab", "ap-south-1") if d["kind"] == "ValidatingAdmissionPolicy")
        self.assertIn("externalIPs", policy["spec"]["validations"][0]["expression"])

    def test_network_policy_has_no_unrestricted_ingress_or_egress(self):
        policy = next(d for d in namespace_documents(SHARED, settings("g001")) if d["kind"] == "NetworkPolicy")
        self.assertEqual(set(policy["spec"]["policyTypes"]), {"Ingress", "Egress"})
        for direction in ("ingress", "egress"):
            self.assertNotIn({}, policy["spec"][direction])
        external = policy["spec"]["egress"][-1]
        self.assertEqual(external["ports"], [{"protocol": "TCP", "port": 443}])
        self.assertIn("169.254.0.0/16", external["to"][0]["ipBlock"]["except"])

    def test_all_database_clients_get_tls_configuration(self):
        database = {"host": "db.example.com", "username": "etp_g001", "database": "etp_g001", "password": "test-password"}
        secret = application_secret(database, {"JWT_SECRET": "test-jwt"}, "etp-g001")
        values = {k: base64.b64decode(v).decode() for k, v in secret["data"].items()}
        self.assertIn("sslmode=verify-full", values["DATABASE_URL"])
        self.assertIn("sslmode=verify-full", values["SPRING_DATASOURCE_URL"])
        self.assertEqual(values["DB_URL"], values["SPRING_DATASOURCE_URL"])
        for name in ("DB_PASSWORD", "PGPASSWORD", "PG_PASSWORD"):
            self.assertEqual(values[name], database["password"])

    def test_cloudformation_release_role_has_no_provisioning_or_admin_secrets(self):
        template, errors = decode(str(ROOT / "student.yaml"))
        self.assertFalse(errors)
        statements = template["Resources"]["ReleaseRole"]["Properties"]["Policies"][0]["PolicyDocument"]["Statement"]
        actions = []
        for statement in statements:
            value = statement["Action"]
            actions.extend([value] if isinstance(value, str) else value)
        self.assertFalse(any(a.startswith(("iam:", "secretsmanager:", "rds:", "ec2:")) for a in actions))
        self.assertFalse(any(a in {"cloudformation:UpdateStack", "cloudformation:CreateStack", "cloudformation:ExecuteChangeSet"} for a in actions))

    def test_analytics_ingress_does_not_publish_the_database_file(self):
        template, _ = decode(str(ROOT / "student.yaml"))
        conditions = template["Resources"]["AnalyticsRule"]["Properties"]["Conditions"]
        paths = next(c["Values"] for c in conditions if c["Field"] == "path-pattern")
        self.assertEqual(paths, ["/", "/index.html"])

    def test_jenkins_embedded_python_survives_groovy_escaping(self):
        source = (ROOT.parent / "Jenkinsfile.example").read_text()
        script = re.search(r"<<'PY'\n(.*?)\nPY", source, re.S).group(1)
        # Groovy processes escapes in a triple-single-quoted shell string first.
        script = script.replace("\\\\", "\0").replace("\\n", "\n").replace("\0", "\\")
        ast.parse(script)

    def test_mutable_or_missing_application_images_are_rejected(self):
        images = {key: "registry.example.com/app:abc1234" for key in ("tradeApi", "tradeExecutor", "auth", "analytics")}
        self.assertEqual(release_values(settings("g001"), images, "jfrog-pull")["frontendUrl"], settings("g001")["FrontendUrl"])
        for bad_image in ("registry/app:latest", "registry/app", ""):
            with self.assertRaises(ValueError):
                release_values(settings("g001"), {**images, "tradeApi": bad_image}, "jfrog-pull")


if __name__ == "__main__":
    unittest.main()
