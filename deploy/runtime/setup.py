"""CloudFormation setup for the shared platform and individual learner environments."""
import base64
import hashlib
import json
import os
from pathlib import Path
import re
import subprocess
import sys
import time
import urllib.request

import boto3
import psycopg
from psycopg import sql
import yaml

from bootstrap_platform import bootstrap
from environment import apply, application_secret, initialise_database, namespace_documents, resource
from integrations import jenkins, jfrog, provision_registry, delete_registry, put_job, stop_job, delete_job

ROOT = Path(__file__).resolve().parent


def validate(event, config):
    if event["ResourceType"] == "Custom::FidelityPlatform":
        if event["StackId"] != config["SharedStackId"] or event["LogicalResourceId"] != "PlatformBootstrap":
            raise ValueError("Invalid shared stack")
        return None
    student = event["StackId"].split("/")[1]
    props = event["ResourceProperties"]
    if event["ResourceType"] != "Custom::FidelityLearner" or event["LogicalResourceId"] != "EnvironmentSetup":
        raise ValueError("Use the supplied learner template")
    if not re.fullmatch(r"s[0-9]{3}", student) or not 1 <= int(student[1:]) <= int(config["StudentCount"]):
        raise ValueError("Use your assigned stack name, such as s001")
    if props["EnvironmentId"] != student or props["PlatformName"] != config["PlatformName"]:
        raise ValueError("Environment does not match this stack")
    if props["Namespace"] != "etp-" + student or props["ClusterName"] != config["ClusterName"]:
        raise ValueError("Invalid environment settings")
    if event["RequestType"] != "Delete":
        pattern = r"https://github\.com/" + re.escape(config["GitHubOrganisation"]) + r"/[A-Za-z0-9_.-]+(?:\.git)?"
        if not re.fullmatch(pattern, props["GitHubRepository"], re.I):
            raise ValueError("Use a repository in the approved GitHub organisation")
        if ".." in props["GitHubBranch"] or props["GitHubBranch"].endswith(("/", ".lock")):
            raise ValueError("Invalid Git branch")
    return student


def connect_cluster(config):
    cluster = boto3.client("eks").describe_cluster(name=config["ClusterName"])["cluster"]
    document = {"apiVersion": "v1", "kind": "Config", "current-context": "lab",
        "clusters": [{"name": "lab", "cluster": {"server": cluster["endpoint"],
            "certificate-authority-data": cluster["certificateAuthority"]["data"]}}],
        "contexts": [{"name": "lab", "context": {"cluster": "lab", "user": "setup"}}],
        "users": [{"name": "setup", "user": {"exec": {"apiVersion": "client.authentication.k8s.io/v1beta1",
            "command": sys.executable, "args": [str(ROOT / "eks_token.py"), config["ClusterName"], config["Region"]],
            "interactiveMode": "Never"}}}]}
    Path("/tmp/kubeconfig").write_text(yaml.safe_dump(document))


def read_secret(arn):
    return json.loads(boto3.client("secretsmanager").get_secret_value(SecretId=arn)["SecretString"])


def empty_bucket(bucket):
    s3 = boto3.client("s3")
    while True:
        page = s3.list_object_versions(Bucket=bucket, MaxKeys=1000)
        objects = [{"Key": x["Key"], "VersionId": x["VersionId"]}
                   for key in ("Versions", "DeleteMarkers") for x in page.get(key, [])]
        if not objects:
            return
        if s3.delete_objects(Bucket=bucket, Delete={"Objects": objects, "Quiet": True}).get("Errors"):
            raise RuntimeError("Could not empty the learner bucket")


def stop_builds(project):
    client = boto3.client("codebuild")
    ids = client.list_builds_for_project(projectName=project, sortOrder="DESCENDING")["ids"][:100]
    if not ids:
        return
    active = [b["id"] for b in client.batch_get_builds(ids=ids)["builds"] if not b["buildComplete"]]
    for build in active:
        client.stop_build(id=build)
    deadline = time.monotonic() + 90
    while active and time.monotonic() < deadline:
        active = [b["id"] for b in client.batch_get_builds(ids=active)["builds"] if not b["buildComplete"]]
        if active:
            time.sleep(5)
    if active:
        raise RuntimeError("Build did not stop. Retry deletion after it finishes.")


def remove_environment(event, config, student):
    props = event["ResourceProperties"]
    j = jenkins(read_secret(config["JenkinsSecretArn"]))
    project = config["PlatformName"] + "-" + student
    stop_job(j, project, event["StackId"])
    stop_builds(project)
    connect_cluster(config)
    subprocess.run(["kubectl", "delete", "targetgroupbindings", "--all", "-n", props["Namespace"],
                    "--ignore-not-found=true", "--timeout=120s"], check=True, timeout=150)
    subprocess.run(["kubectl", "delete", "namespace", props["Namespace"],
                    "--ignore-not-found=true", "--timeout=180s"], check=True, timeout=210)
    admin = read_secret(config["DatabaseAdminSecretArn"])
    database = "etp_" + student
    with psycopg.connect(host=config["DatabaseHost"], dbname="postgres", user=admin["username"],
                          password=admin["password"], sslmode="verify-full", sslrootcert=str(ROOT / "rds-ca.pem"),
                          connect_timeout=15, autocommit=True) as conn:
        conn.execute(sql.SQL("DROP DATABASE IF EXISTS {} WITH (FORCE)").format(sql.Identifier(database)))
        conn.execute(sql.SQL("DROP ROLE IF EXISTS {}").format(sql.Identifier(database)))
    registry = read_secret(config["JFrogSecretArn"])
    delete_registry(jfrog(registry), registry, config["PlatformName"], student)
    empty_bucket(props["BucketName"])
    delete_job(j, project, event["StackId"])
    return {}


def configure_environment(event, config, student):
    props = event["ResourceProperties"]
    connect_cluster(config)
    database = read_secret(props["DatabaseSecretArn"])
    initialise_database(read_secret(config["DatabaseAdminSecretArn"]), database, ROOT / "rds-ca.pem", [])
    apply(namespace_documents(config, props))
    apply([resource("ConfigMap", "rds-ca", props["Namespace"], data={"ca.pem": (ROOT / "rds-ca.pem").read_text()}),
           application_secret(database, read_secret(props["JwtSecretArn"]), props["Namespace"])])
    registry = read_secret(config["JFrogSecretArn"])
    credential = read_secret(props["RegistrySecretArn"])
    provision_registry(jfrog(registry), registry, credential, config["PlatformName"], student)
    credential.update(RegistryHost=registry["registryHost"],
                      ImagePrefix=f"{registry['registryHost']}/{registry['dockerRepository']}/{config['PlatformName']}/{student}")
    boto3.client("secretsmanager").put_secret_value(SecretId=props["RegistrySecretArn"], SecretString=json.dumps(credential))
    auth = base64.b64encode((credential["username"] + ":" + credential["password"]).encode()).decode()
    docker = {"auths": {registry["registryHost"]: {"auth": auth}}}
    apply([resource("Secret", "jfrog-pull", props["Namespace"], type="kubernetes.io/dockerconfigjson",
                    data={".dockerconfigjson": base64.b64encode(json.dumps(docker).encode()).decode()})])
    j = jenkins(read_secret(config["JenkinsSecretArn"]))
    url = put_job(j, config, student, props["BuildProjectName"], props["GitHubRepository"],
                  props["GitHubBranch"], event["StackId"])
    j.request("/job/" + config["PlatformName"] + "-" + student + "/build", "POST", b"")
    return {"JenkinsUrl": url, **{k: props[k] for k in ("ApiUrl", "AuthUrl", "AnalyticsUrl")}}


def handler(event, context):
    os.environ["PATH"] = str(ROOT / "bin") + ":" + os.environ["PATH"]
    config = json.loads(os.environ["CONFIG_JSON"])
    physical = event.get("PhysicalResourceId") or hashlib.sha256(event["StackId"].encode()).hexdigest()[:24]
    status, data, reason = "SUCCESS", {}, ""
    try:
        student = validate(event, config)
        if student:
            data = remove_environment(event, config, student) if event["RequestType"] == "Delete" else configure_environment(event, config, student)
        elif event["RequestType"] != "Delete":
            connect_cluster(config)
            bootstrap(config, config["Region"])
            jenkins(read_secret(config["JenkinsSecretArn"])).request("/api/json?tree=mode")
            registry = read_secret(config["JFrogSecretArn"])
            jfrog(registry).request("/artifactory/api/repositories/" + registry["dockerRepository"])
            data = {"Status": "Ready for pilot"}
    except Exception as error:
        status = "FAILED"
        reason = str(error) if isinstance(error, (ValueError, RuntimeError)) else type(error).__name__
        print("Setup failed: " + reason[:500])
    body = json.dumps({"Status": status, "Reason": reason[:500] or "Setup complete",
        "PhysicalResourceId": physical, "StackId": event["StackId"], "RequestId": event["RequestId"],
        "LogicalResourceId": event["LogicalResourceId"], "Data": data}).encode()
    request = urllib.request.Request(event["ResponseURL"], method="PUT", data=body,
                                     headers={"Content-Type": "", "Content-Length": str(len(body))})
    with urllib.request.urlopen(request, timeout=20):
        pass
