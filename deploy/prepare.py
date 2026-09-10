#!/usr/bin/env python3
"""Engineering preparation and student database migrations, run by Jenkins."""

from __future__ import annotations

import hashlib
import argparse
import base64
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
from urllib.parse import quote

import boto3
import psycopg
from psycopg import sql
import yaml


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
            # Helm stores its release records as Secrets. These credentials belong only to this student.
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
    migrate_database(database, ca_path, migrations)


def migrate_database(database, ca_path, migrations):
    common = {"host": database["host"], "port": int(database["port"]),
              "sslmode": "verify-full", "sslrootcert": str(ca_path.resolve()), "connect_timeout": 15}
    with psycopg.connect(**common, dbname=database["database"], user=database["username"], password=database["password"]) as conn:
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
    return resource("Secret", "application-config", namespace, type="Opaque",
                    data={k: base64.b64encode(v.encode()).decode() for k, v in values.items()})


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("action", choices=["prepare", "migrate"])
    parser.add_argument("--region", required=True)
    parser.add_argument("--student", required=True)
    parser.add_argument("--shared-stack")
    parser.add_argument("--outputs", type=Path, default=Path("environment.json"))
    parser.add_argument("--ca", type=Path, default=Path("/opt/fidelity/rds-ca.pem"))
    parser.add_argument("--migrations", type=Path, default=Path("infra/postgres"))
    args = parser.parse_args()
    if not re.fullmatch(r"s[0-9]{3}", args.student):
        parser.error("Use the assigned student ID, such as s001")
    session = boto3.Session(region_name=args.region)
    cf, secrets = session.client("cloudformation"), session.client("secretsmanager")

    def outputs(name):
        stack = cf.describe_stacks(StackName=name)["Stacks"][0]
        if stack["StackStatus"] not in ("CREATE_COMPLETE", "UPDATE_COMPLETE"):
            raise ValueError("CloudFormation stack is not ready: " + name)
        return {o["OutputKey"]: o["OutputValue"] for o in stack["Outputs"]}

    def secret(arn):
        return json.loads(secrets.get_secret_value(SecretId=arn)["SecretString"])

    student = outputs(args.student)
    if student["EnvironmentId"] != args.student or student["Namespace"] != "etp-" + args.student:
        raise ValueError("Stack does not match the assigned student")
    database = secret(student["DatabaseSecretArn"])
    if args.action == "migrate":
        migrations = sorted(args.migrations.glob("*.sql"))
        if not migrations:
            raise ValueError("No SQL migrations found in " + str(args.migrations))
        migrate_database(database, args.ca, migrations)
        return
    if not args.shared_stack:
        parser.error("prepare requires --shared-stack")
    shared = outputs(args.shared_stack)
    if any(student[k] != shared[k] for k in ("PlatformName", "ClusterName", "DatabaseHost")):
        raise ValueError("Student stack belongs to a different shared platform")
    initialise_database(secret(shared["DatabaseAdminSecretArn"]), database, args.ca, [])
    with tempfile.TemporaryDirectory() as directory:
        os.environ["KUBECONFIG"] = str(Path(directory) / "config")
        subprocess.run(["aws", "eks", "update-kubeconfig", "--name", shared["ClusterName"], "--region", args.region], check=True)
        apply(namespace_documents(shared, student))
        auth = base64.b64encode((os.environ["JFROG_USER"] + ":" + os.environ["JFROG_TOKEN"]).encode()).decode()
        docker = {"auths": {os.environ["JFROG_HOST"]: {"auth": auth}}}
        apply([application_secret(database, secret(student["JwtSecretArn"]), student["Namespace"]),
               resource("ConfigMap", "rds-ca", student["Namespace"], data={"ca.pem": args.ca.read_text()}),
               resource("Secret", "jfrog-pull", student["Namespace"], type="kubernetes.io/dockerconfigjson",
                        data={".dockerconfigjson": base64.b64encode(json.dumps(docker).encode()).decode()})])
    args.outputs.write_text(json.dumps(student, indent=2) + "\n")


if __name__ == "__main__":
    main()
