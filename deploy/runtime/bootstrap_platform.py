#!/usr/bin/env python3
"""Install the Kubernetes components that complement shared.yaml."""

import subprocess
from pathlib import Path


from environment import apply


def platform_documents(platform, region):
    config = f"""[SERVICE]
    Flush 5
    Log_Level warn
    Parsers_File /fluent-bit/parsers/parsers.conf
[INPUT]
    Name tail
    Path /var/log/containers/*_etp-*_*.log
    Tag kube.*
    multiline.parser docker, cri
    DB /var/fluent-bit/state/tail.db
    Mem_Buf_Limit 10MB
    Skip_Long_Lines On
    Read_From_Head Off
[FILTER]
    Name kubernetes
    Match kube.*
    Merge_Log On
    Keep_Log On
    Labels Off
    Annotations Off
[FILTER]
    Name grep
    Match kube.*
    Regex $kubernetes['namespace_name'] ^etp-
[OUTPUT]
    Name cloudwatch_logs
    Match kube.*
    region {region}
    log_group_name /fidelity/{platform}/unknown
    log_group_template /fidelity/{platform}/$kubernetes['namespace_name']
    log_stream_prefix application-
    auto_create_group false
    Retry_Limit 5
"""
    ns = "amazon-cloudwatch"
    return [
        {"apiVersion": "storage.k8s.io/v1", "kind": "StorageClass", "metadata": {"name": "etp-gp3"},
         "provisioner": "ebs.csi.aws.com", "parameters": {"type": "gp3", "encrypted": "true"},
         "volumeBindingMode": "WaitForFirstConsumer", "allowVolumeExpansion": True, "reclaimPolicy": "Delete"},
        {"apiVersion": "admissionregistration.k8s.io/v1", "kind": "ValidatingAdmissionPolicy",
         "metadata": {"name": "etp-clusterip-services"}, "spec": {
             "failurePolicy": "Fail",
             "matchConstraints": {"resourceRules": [{"apiGroups": [""], "apiVersions": ["v1"], "operations": ["CREATE", "UPDATE"], "resources": ["services"]}]},
             "validations": [{"expression": "(!has(object.spec.type) || object.spec.type == 'ClusterIP') && (!has(object.spec.externalIPs) || size(object.spec.externalIPs) == 0)",
                              "message": "Training services must use ClusterIP without externalIPs. Engineering owns public routing."}],
         }},
        {"apiVersion": "admissionregistration.k8s.io/v1", "kind": "ValidatingAdmissionPolicyBinding",
         "metadata": {"name": "etp-clusterip-services"}, "spec": {
             "policyName": "etp-clusterip-services", "validationActions": ["Deny"],
             "matchResources": {"namespaceSelector": {"matchLabels": {"etp-environment": "true"}}},
         }},
        {"apiVersion": "v1", "kind": "Namespace", "metadata": {"name": ns}},
        {"apiVersion": "v1", "kind": "ServiceAccount", "metadata": {"name": "fluent-bit", "namespace": ns}},
        {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "ClusterRole", "metadata": {"name": "etp-fluent-bit"},
         "rules": [{"apiGroups": [""], "resources": ["pods", "namespaces"], "verbs": ["get", "list", "watch"]}]},
        {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "ClusterRoleBinding", "metadata": {"name": "etp-fluent-bit"},
         "subjects": [{"kind": "ServiceAccount", "name": "fluent-bit", "namespace": ns}],
         "roleRef": {"apiGroup": "rbac.authorization.k8s.io", "kind": "ClusterRole", "name": "etp-fluent-bit"}},
        {"apiVersion": "v1", "kind": "ConfigMap", "metadata": {"name": "fluent-bit", "namespace": ns}, "data": {"fluent-bit.conf": config}},
        {"apiVersion": "apps/v1", "kind": "DaemonSet", "metadata": {"name": "fluent-bit", "namespace": ns}, "spec": {
            "selector": {"matchLabels": {"app": "fluent-bit"}},
            "template": {"metadata": {"labels": {"app": "fluent-bit"}}, "spec": {
                "serviceAccountName": "fluent-bit", "nodeSelector": {"kubernetes.io/os": "linux"},
                "containers": [{"name": "fluent-bit", "image": "public.ecr.aws/aws-observability/aws-for-fluent-bit:3.2.1",
                                "resources": {"requests": {"cpu": "50m", "memory": "128Mi"}, "limits": {"cpu": "500m", "memory": "256Mi"}},
                                "volumeMounts": [
                                    {"name": "logs", "mountPath": "/var/log", "readOnly": True},
                                    {"name": "state", "mountPath": "/var/fluent-bit/state"},
                                    {"name": "config", "mountPath": "/fluent-bit/etc/fluent-bit.conf", "subPath": "fluent-bit.conf", "readOnly": True},
                                ]}],
                "volumes": [{"name": "logs", "hostPath": {"path": "/var/log", "type": "Directory"}},
                            {"name": "state", "hostPath": {"path": "/var/lib/etp-fluent-bit", "type": "DirectoryOrCreate"}},
                            {"name": "config", "configMap": {"name": "fluent-bit"}}],
            }},
        }},
    ]


def bootstrap(shared, region):
    subprocess.run([
        "helm", "upgrade", "--install", "aws-load-balancer-controller", str(Path(__file__).parent / "controller.tgz"),
        "--namespace", "kube-system",
        "--set", f"clusterName={shared['ClusterName']}", "--set", f"region={region}",
        "--set", f"vpcId={shared['VpcId']}", "--set", "serviceAccount.name=aws-load-balancer-controller",
        "--set", "enableServiceMutatorWebhook=false", "--set", "enableBackendSecurityGroup=false",
        "--set", "enableShield=false", "--set", "enableWaf=false", "--set", "enableWafv2=false",
        "--wait", "--timeout", "300s",
    ], check=True, timeout=330)
    apply(platform_documents(shared["PlatformName"], region))
    subprocess.run(["kubectl", "rollout", "status", "daemonset/fluent-bit", "-n", "amazon-cloudwatch", "--timeout=120s"], check=True, timeout=150)
