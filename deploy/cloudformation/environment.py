#!/usr/bin/env python3
"""Prepare parameters or bootstrap one environment as the platform engineer.

Secrets stay in memory and go to kubectl through stdin. No application secret
or administrator password is written to a local output file.
"""

from __future__ import annotations

import argparse
import hashlib
import json
from pathlib import Path
import re
import subprocess
from urllib.parse import quote

import boto3
import psycopg
from psycopg import sql
import yaml


def outputs(client, stack):
    result = client.describe_stacks(StackName=stack)["Stacks"][0]
    if result["StackStatus"] not in {"CREATE_COMPLETE", "UPDATE_COMPLETE"}:
        raise ValueError(f"Stack {stack} is not ready: {result['StackStatus']}")
    return {item["OutputKey"]: item["OutputValue"] for item in result["Outputs"]}


def apply(documents):
    subprocess.run(
        ["kubectl", "apply", "--server-side", "--field-manager=etp-platform", "-f", "-"],
        input=yaml.safe_dump_all(documents), text=True, check=True,
    )


def resource(kind, name, namespace, **extra):
    return {"apiVersion": "v1", "kind": kind,
            "metadata": {"name": name, "namespace": namespace}, **extra}


def namespace_documents(shared, student):
    ns, env = student["Namespace"], student["EnvironmentId"]
    namespace = {
        "apiVersion": "v1", "kind": "Namespace",
        "metadata": {"name": ns, "labels": {
            "etp-environment": "true", "pod-security.kubernetes.io/enforce": "restricted",
            "pod-security.kubernetes.io/audit": "restricted",
            "pod-security.kubernetes.io/warn": "restricted",
        }},
    }
    quota = resource("ResourceQuota", "environment", ns, spec={"hard": {
        "requests.cpu": "6", "requests.memory": "10Gi",
        "limits.cpu": "16", "limits.memory": "16Gi", "pods": "16",
        "requests.storage": "30Gi", "persistentvolumeclaims": "2",
        "services.loadbalancers": "0", "services.nodeports": "0",
    }})
    limit = resource("LimitRange", "environment", ns, spec={"limits": [{
        "type": "Container", "defaultRequest": {"cpu": "100m", "memory": "128Mi"},
        "default": {"cpu": "1", "memory": "1Gi"},
    }]})
    sa = resource("ServiceAccount", "application", ns, automountServiceAccountToken=False)
    role = {
        "apiVersion": "rbac.authorization.k8s.io/v1", "kind": "Role",
        "metadata": {"name": "release", "namespace": ns},
        "rules": [
            {"apiGroups": ["apps"], "resources": ["deployments", "deployments/scale", "statefulsets", "statefulsets/scale", "replicasets"],
             "verbs": ["get", "list", "watch", "create", "update", "patch", "delete"]},
            {"apiGroups": ["batch"], "resources": ["jobs"], "verbs": ["get", "list", "watch", "create", "update", "patch", "delete"]},
            # Helm stores its release records as Secrets. These credentials belong only to this group.
            {"apiGroups": [""], "resources": ["services", "configmaps", "secrets"],
             "verbs": ["get", "list", "watch", "create", "update", "patch", "delete"]},
            {"apiGroups": [""], "resources": ["pods", "pods/log", "events", "persistentvolumeclaims", "serviceaccounts"],
             "verbs": ["get", "list", "watch"]},
        ],
    }
    binding = {"apiVersion": "rbac.authorization.k8s.io/v1", "kind": "RoleBinding",
               "metadata": {"name": "release", "namespace": ns},
               "subjects": [{"kind": "Group", "name": f"etp:{env}:deploy", "apiGroup": "rbac.authorization.k8s.io"}],
               "roleRef": {"kind": "Role", "name": "release", "apiGroup": "rbac.authorization.k8s.io"}}
    own_namespace = {"podSelector": {}}
    network = {
        "apiVersion": "networking.k8s.io/v1", "kind": "NetworkPolicy",
        "metadata": {"name": "environment-isolation", "namespace": ns},
        "spec": {
            "podSelector": {}, "policyTypes": ["Ingress", "Egress"],
            "ingress": [
                {"from": [own_namespace]},
                {"from": [{"ipBlock": {"cidr": shared[k]}} for k in ("PublicSubnetCidrA", "PublicSubnetCidrB")],
                 "ports": [{"protocol": "TCP", "port": p} for p in (3000, 8000, 8080)]},
            ],
            "egress": [
                {"to": [own_namespace]},
                {"to": [{"namespaceSelector": {"matchLabels": {"kubernetes.io/metadata.name": "kube-system"}},
                         "podSelector": {"matchLabels": {"k8s-app": "kube-dns"}}}],
                 "ports": [{"protocol": p, "port": 53} for p in ("TCP", "UDP")]},
                {"to": [{"ipBlock": {"cidr": shared["VpcCidr"]}}], "ports": [{"protocol": "TCP", "port": 5432}]},
                {"to": [{"ipBlock": {"cidr": "0.0.0.0/0", "except": ["10.0.0.0/8", "172.16.0.0/12", "192.168.0.0/16", "169.254.0.0/16"]}}],
                 "ports": [{"protocol": "TCP", "port": 443}]},
            ],
        },
    }
    documents = [namespace, quota, limit, sa, role, binding, network]
    for name in ("kafka-data", "analytics-data"):
        documents.append(resource("PersistentVolumeClaim", name, ns, spec={
            "accessModes": ["ReadWriteOnce"], "storageClassName": "etp-gp3",
            "resources": {"requests": {"storage": "10Gi"}},
        }))
    for name, key, port in (("trade-api", "ApiTargetGroupArn", 8080),
                            ("auth-service", "AuthTargetGroupArn", 3000),
                            ("analytics", "AnalyticsTargetGroupArn", 8000)):
        documents.append({
            "apiVersion": "elbv2.k8s.aws/v1beta1", "kind": "TargetGroupBinding",
            "metadata": {"name": name, "namespace": ns},
            "spec": {"targetGroupARN": student[key], "targetType": "ip", "vpcID": shared["VpcId"],
                     "serviceRef": {"name": name, "port": port}},
        })
    return documents


def initialise_database(admin, database, ca_path, migrations):
    # Only the platform engineer runs this function. Release jobs never receive admin credentials.
    common = {"host": database["host"], "port": int(database["port"]),
              "sslmode": "verify-full", "sslrootcert": str(ca_path.resolve()), "connect_timeout": 15}
    role_name, db_name = database["username"], database["database"]
    with psycopg.connect(**common, dbname="postgres", user=admin["username"], password=admin["password"], autocommit=True) as conn:
        # Lock by database name so two provisioning jobs cannot race CREATE ROLE/DATABASE.
        conn.execute("SELECT pg_advisory_lock(hashtext(%s))", (db_name,))
        if not conn.execute("SELECT 1 FROM pg_roles WHERE rolname = %s", (role_name,)).fetchone():
            conn.execute(sql.SQL("CREATE ROLE {} LOGIN NOINHERIT NOSUPERUSER NOCREATEDB NOCREATEROLE NOREPLICATION CONNECTION LIMIT 20").format(sql.Identifier(role_name)))
        conn.execute(sql.SQL("ALTER ROLE {} PASSWORD {}").format(sql.Identifier(role_name), sql.Literal(database["password"])))
        conn.execute(sql.SQL("GRANT {} TO CURRENT_USER").format(sql.Identifier(role_name)))
        if not conn.execute("SELECT 1 FROM pg_database WHERE datname = %s", (db_name,)).fetchone():
            conn.execute(sql.SQL("CREATE DATABASE {} OWNER {}").format(sql.Identifier(db_name), sql.Identifier(role_name)))
        conn.execute(sql.SQL("REVOKE ALL ON DATABASE {} FROM PUBLIC").format(sql.Identifier(db_name)))
    with psycopg.connect(**common, dbname=db_name, user=role_name, password=database["password"]) as conn:
        conn.execute("REVOKE CREATE ON SCHEMA public FROM PUBLIC")
        conn.execute("CREATE TABLE IF NOT EXISTS etp_migrations (name text PRIMARY KEY, checksum text NOT NULL, applied_at timestamptz NOT NULL DEFAULT now())")
        conn.execute("SELECT pg_advisory_xact_lock(hashtext('etp_migrations'))")
        for path in migrations:
            content = path.read_text()
            checksum = hashlib.sha256(content.encode()).hexdigest()
            existing = conn.execute("SELECT checksum FROM etp_migrations WHERE name=%s", (path.name,)).fetchone()
            if existing:
                if existing[0] != checksum:
                    raise ValueError(f"Applied migration changed: {path.name}; add a new migration instead")
                continue
            conn.execute(content)
            conn.execute("INSERT INTO etp_migrations(name, checksum) VALUES (%s, %s)", (path.name, checksum))
            print(f"Applied migration {path.name}")


def application_secret(database, jwt, namespace):
    host, user, name, password = (database[k] for k in ("host", "username", "database", "password"))
    jdbc = f"jdbc:postgresql://{host}:5432/{name}?sslmode=verify-full&sslrootcert=/etc/rds/ca.pem"
    uri = f"postgresql://{quote(user, safe='')}:{quote(password, safe='')}@{host}:5432/{name}?sslmode=verify-full&sslrootcert=/etc/rds/ca.pem"
    values = {"DB_HOST": host, "DB_PORT": "5432", "DB_NAME": name, "DB_USER": user,
              "DB_USERNAME": user, "DB_PASSWORD": password, "DB_URL": jdbc,
              "SPRING_DATASOURCE_URL": jdbc, "DATABASE_URL": uri,
              "PGHOST": host, "PGPORT": "5432", "PGDATABASE": name, "PGUSER": user, "PGPASSWORD": password,
              "PG_HOST": host, "PG_PORT": "5432", "PG_DATABASE": name, "PG_USER": user, "PG_PASSWORD": password,
              "JWT_SECRET": jwt["JWT_SECRET"]}
    # Use data rather than stringData for repeatable server-side apply.
    import base64
    return resource("Secret", "application-config", namespace, type="Opaque",
                    data={k: base64.b64encode(v.encode()).decode() for k, v in values.items()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", required=True)
    parser.add_argument("--shared-stack", required=True)
    sub = parser.add_subparsers(dest="action", required=True)
    parameters = sub.add_parser("parameters", help="Write non-secret student stack parameters")
    parameters.add_argument("--environment", required=True)
    parameters.add_argument("--agent-role", required=True)
    parameters.add_argument("--alb", choices=["A", "B"], default="A")
    parameters.add_argument("--slot", type=int, choices=range(1, 31), required=True)
    parameters.add_argument("--output", type=Path, required=True)
    bootstrap = sub.add_parser("bootstrap", help="Create group database, namespace and supporting Kubernetes resources")
    bootstrap.add_argument("--student-stack", required=True)
    bootstrap.add_argument("--rds-ca", type=Path, required=True)
    bootstrap.add_argument("--migration", type=Path, action="append", required=True)
    bootstrap.add_argument("--output", type=Path, required=True, help="Non-secret stack outputs for release automation")
    args = parser.parse_args()
    session = boto3.Session(region_name=args.region)
    cf = session.client("cloudformation")
    shared = outputs(cf, args.shared_stack)
    if args.action == "parameters":
        if not re.fullmatch(r"[a-z][a-z0-9]{2,15}", args.environment):
            parser.error("Use an environment ID such as g001 or s001")
        data = {key: shared[key] for key in ("PlatformName", "ClusterName", "DatabaseHost", "VpcId", "HostedZoneId", "BaseDomain")}
        data.update(EnvironmentId=args.environment, JenkinsAgentRoleArn=args.agent_role, ListenerSlot=str(args.slot),
                    ListenerArn=shared[f"ListenerArn{args.alb}"], AlbDnsName=shared[f"AlbDns{args.alb}"], AlbHostedZoneId=shared[f"AlbZone{args.alb}"])
        args.output.write_text(json.dumps([{"ParameterKey": k, "ParameterValue": v} for k, v in data.items()], indent=2) + "\n")
        print(f"Wrote non-secret parameters to {args.output}")
        return
    student = outputs(cf, args.student_stack)
    if student["ClusterName"] != shared["ClusterName"] or student["DatabaseHost"] != shared["DatabaseHost"]:
        raise ValueError("Student and shared stacks do not belong to the same platform")
    current = json.loads(subprocess.check_output(["kubectl", "config", "view", "--minify", "-o", "json"]))
    expected = session.client("eks").describe_cluster(name=shared["ClusterName"])["cluster"]["endpoint"]
    if current["clusters"][0]["cluster"]["server"] != expected:
        raise ValueError("kubectl is pointed at a different cluster; run aws eks update-kubeconfig first")
    ca = args.rds_ca.read_text()
    if "BEGIN CERTIFICATE" not in ca:
        raise ValueError("--rds-ca must contain the AWS RDS CA bundle")
    secrets = session.client("secretsmanager")
    def read_secret(arn):
        return json.loads(secrets.get_secret_value(SecretId=arn)["SecretString"])
    database = read_secret(student["DatabaseSecretArn"])
    jwt = read_secret(student["JwtSecretArn"])
    initialise_database(read_secret(shared["DatabaseAdminSecretArn"]), database, args.rds_ca, args.migration)
    apply(namespace_documents(shared, student))
    apply([resource("ConfigMap", "rds-ca", student["Namespace"], data={"ca.pem": ca}),
           application_secret(database, jwt, student["Namespace"])])
    args.output.write_text(json.dumps(student, indent=2) + "\n")
    print(f"Bootstrapped {student['Namespace']}; public release settings written to {args.output}")


if __name__ == "__main__":
    main()
