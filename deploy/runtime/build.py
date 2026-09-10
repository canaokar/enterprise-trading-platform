"""Jenkins release work executed in an isolated, student-scoped CodeBuild worker."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile

import boto3
from environment import migrate_database


def run(arguments, directory, **kwargs):
    subprocess.run(arguments, cwd=directory, check=True, **kwargs)


def main():
    runtime = Path(__file__).resolve().parent
    source = Path(os.environ["CODEBUILD_SRC_DIR_application"])
    settings = json.loads(os.environ["SETTINGS_JSON"])
    if settings["EnvironmentId"] != os.environ["ENVIRONMENT_ID"]:
        raise ValueError("Wrong environment configuration")
    commit = subprocess.check_output(["git", "rev-parse", "HEAD"], cwd=source, text=True).strip()
    run(["mvn", "-B", "-f", "services/trade-api/pom.xml", "test"], source)
    run(["mvn", "-B", "-f", "services/trade-executor/pom.xml", "test"], source)
    run(["npm", "--prefix", "services/auth-service", "ci"], source)
    run(["npm", "--prefix", "services/auth-service", "test", "--", "--runInBand"], source)
    run(["npm", "--prefix", "ui", "ci"], source)
    run(["npm", "--prefix", "ui", "test"], source)
    run([sys.executable, "-m", "pip", "install", "-e", "./analytics[dev]"], source)
    run([sys.executable, "-m", "pytest", "analytics/tests"], source)
    secret = json.loads(boto3.client("secretsmanager").get_secret_value(
        SecretId=settings["RegistrySecretArn"])["SecretString"])
    settings.update({k: secret[k] for k in ("RegistryHost", "ImagePrefix")})
    Path("/tmp/environment.json").write_text(json.dumps(settings))
    images = {}
    with tempfile.TemporaryDirectory(prefix="etp-docker-") as directory:
        child = {**os.environ, "DOCKER_CONFIG": directory}
        run(["docker", "login", settings["RegistryHost"], "--username", secret["username"], "--password-stdin"],
            source, input=secret["password"], text=True, env=child)
        for key, name, context in (("tradeApi", "trade-api", "services/trade-api"),
                                    ("tradeExecutor", "trade-executor", "services/trade-executor"),
                                    ("auth", "auth-service", "services/auth-service"),
                                    ("analytics", "analytics", "analytics")):
            image = f"{settings['ImagePrefix']}/{name}:{commit}"
            run(["docker", "build", "--platform", "linux/amd64", "--tag", image, context], source, env=child)
            run(["docker", "push", image], source, env=child)
            digest = subprocess.check_output(["docker", "inspect", "--format", "{{index .RepoDigests 0}}", image],
                                              cwd=source, env=child, text=True).strip()
            images[key] = digest
    config = {"production": True, "tradeApiBaseUrl": settings["ApiUrl"], "authApiBaseUrl": settings["AuthUrl"],
              "orderPollIntervalMs": 2000, "orderPollAttempts": 10}
    (source / "ui/src/environments/environment.ts").write_text("export const environment = " + json.dumps(config) + ";\n")
    run(["npm", "--prefix", "ui", "run", "build"], source)
    database = json.loads(boto3.client("secretsmanager").get_secret_value(
        SecretId=settings["DatabaseSecretArn"])["SecretString"])
    migrations = sorted((source / "infra/postgres").glob("*.sql"))
    if not migrations:
        raise ValueError("Repository must supply ordered SQL migrations in infra/postgres")
    migrate_database(database, Path("/tmp/rds-ca.pem"), migrations)
    Path("/tmp/images.json").write_text(json.dumps(images))
    run([sys.executable, str(runtime / "release.py"), "--region", os.environ["AWS_REGION"],
         "--outputs", "/tmp/environment.json", "--images", "/tmp/images.json",
         "--frontend", str(source / "ui/dist/ui/browser"), "--record", "/tmp/release-record.json"], source)
    record = json.loads(Path("/tmp/release-record.json").read_text())
    record["commit"] = commit
    boto3.client("s3").put_object(Bucket=settings["BucketName"], Key="_releases/" + commit + ".json",
                                 Body=json.dumps(record).encode(), ContentType="application/json")
    print("Released commit " + commit + " to " + settings["FrontendUrl"])


if __name__ == "__main__":
    main()
