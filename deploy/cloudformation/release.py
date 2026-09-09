#!/usr/bin/env python3
"""Release existing images and an Angular build using the group's scoped role."""

import argparse
import json
import os
from pathlib import Path
import re
import subprocess
import tempfile
import urllib.request

import boto3
import yaml


def release_values(outputs, images, pull_secret):
    for key in ("tradeApi", "tradeExecutor", "auth", "analytics"):
        image = images.get(key, "")
        if not re.fullmatch(r"[^\s]+(?:@sha256:[a-f0-9]{64}|:[a-f0-9]{7,40})", image):
            raise ValueError(f"images.{key} must use a commit SHA tag or image digest")
    return {"images": images, "frontendUrl": outputs["FrontendUrl"],
            "imagePullSecrets": [{"name": pull_secret}] if pull_secret else []}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", required=True)
    parser.add_argument("--outputs", type=Path, required=True)
    parser.add_argument("--images", type=Path, required=True)
    parser.add_argument("--frontend", type=Path, required=True)
    parser.add_argument("--pull-secret", default="jfrog-pull")
    parser.add_argument("--record", type=Path, default=Path("release-record.json"))
    args = parser.parse_args()
    settings = json.loads(args.outputs.read_text())
    images = json.loads(args.images.read_text())
    values = release_values(settings, images, args.pull_secret)
    if not (args.frontend / "index.html").is_file():
        parser.error("--frontend must contain the Angular production index.html")
    for bundle in args.frontend.rglob("*.js"):
        if re.search(r"https?://localhost(?::\d+)?", bundle.read_text()):
            parser.error(f"Production bundle still contains a localhost URL: {bundle.name}")
    session = boto3.Session(region_name=args.region)
    credentials = session.client("sts").assume_role(
        RoleArn=settings["ReleaseRoleArn"], RoleSessionName="etp-release", DurationSeconds=3600,
    )["Credentials"]
    child_env = {**os.environ, "AWS_REGION": args.region, "AWS_DEFAULT_REGION": args.region,
                 "AWS_ACCESS_KEY_ID": credentials["AccessKeyId"],
                 "AWS_SECRET_ACCESS_KEY": credentials["SecretAccessKey"],
                 "AWS_SESSION_TOKEN": credentials["SessionToken"]}
    # Environment credentials take precedence; remove profile selectors to avoid ambiguity.
    child_env.pop("AWS_PROFILE", None)
    child_env.pop("AWS_DEFAULT_PROFILE", None)
    chart = Path(__file__).resolve().parents[1] / "helm" / "trading"
    def run(command):
        subprocess.run(command, env=child_env, check=True)
    with tempfile.TemporaryDirectory(prefix="etp-release-") as directory:
        values_path = Path(directory) / "values.yaml"
        values_path.write_text(yaml.safe_dump(values))
        child_env["KUBECONFIG"] = str(Path(directory) / "kubeconfig")
        run(["aws", "eks", "update-kubeconfig", "--name", settings["ClusterName"], "--region", args.region])
        run(["helm", "upgrade", "--install", "trading", str(chart), "--namespace", settings["Namespace"],
             "--values", str(values_path), "--atomic", "--wait", "--wait-for-jobs", "--timeout", "15m", "--history-max", "3"])
        # Upload assets first and retain old hashes so open browser sessions still work.
        bucket = f"s3://{settings['BucketName']}"
        run(["aws", "s3", "sync", str(args.frontend), bucket, "--exclude", "index.html",
             "--cache-control", "public,max-age=31536000,immutable", "--only-show-errors"])
        run(["aws", "s3", "cp", str(args.frontend / "index.html"), bucket + "/index.html",
             "--cache-control", "no-cache,no-store,must-revalidate", "--content-type", "text/html", "--only-show-errors"])
        cloudfront = boto3.client("cloudfront", region_name=args.region,
                                 aws_access_key_id=credentials["AccessKeyId"],
                                 aws_secret_access_key=credentials["SecretAccessKey"],
                                 aws_session_token=credentials["SessionToken"])
        import uuid
        result = cloudfront.create_invalidation(DistributionId=settings["DistributionId"], InvalidationBatch={
            "CallerReference": str(uuid.uuid4()), "Paths": {"Quantity": 1, "Items": ["/*"]},
        })
        cloudfront.get_waiter("invalidation_completed").wait(DistributionId=settings["DistributionId"], Id=result["Invalidation"]["Id"])
    urls = [settings["FrontendUrl"], settings["ApiUrl"] + "/actuator/health",
            settings["AuthUrl"] + "/docs/json", settings["AnalyticsUrl"] + "/index.html"]
    for url in urls:
        with urllib.request.urlopen(url, timeout=30) as response:
            if response.status != 200:
                raise RuntimeError(f"Smoke check failed: {url}")
        print(f"HTTP smoke check passed: {url}")
    args.record.write_text(json.dumps({"environment": settings["EnvironmentId"], "images": images,
                                      "frontendUrl": settings["FrontendUrl"], "httpSmokeChecks": urls}, indent=2) + "\n")
    print("Release complete. Run the authenticated order journey before assessment.")


if __name__ == "__main__":
    main()
