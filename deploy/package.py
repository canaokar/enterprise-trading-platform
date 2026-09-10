"""Package the two CloudFormation entry points and their runtime assets."""
import argparse
import hashlib
import io
import json
from pathlib import Path
import subprocess
import sys
import tarfile
import tempfile
import urllib.request
from urllib.parse import urljoin
import zipfile

import boto3
import yaml

ROOT = Path(__file__).resolve().parent


def fetch(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def checked(url, checksum_url):
    data = fetch(url)
    if hashlib.sha256(data).hexdigest() != fetch(checksum_url).decode().split()[0]:
        raise ValueError("Checksum mismatch: " + url)
    return data


def policy(account, region, platform, student, template_url, execution_role):
    stack = f"arn:aws:cloudformation:{region}:{account}:stack/{student}/*"
    return {"Version": "2012-10-17", "Statement": [
        {"Effect": "Allow", "Action": ["cloudformation:CreateStack", "cloudformation:UpdateStack"], "Resource": stack,
         "Condition": {"StringEquals": {"cloudformation:TemplateUrl": template_url, "cloudformation:RoleARN": execution_role}}},
        {"Effect": "Allow", "Action": ["cloudformation:DeleteStack", "cloudformation:DescribeStacks", "cloudformation:DescribeStackEvents",
                                        "cloudformation:DescribeStackResources", "cloudformation:ListStackResources", "cloudformation:GetTemplate"], "Resource": stack},
        {"Effect": "Allow", "Action": ["cloudformation:ListStacks", "cloudformation:GetTemplateSummary", "cloudformation:ValidateTemplate"], "Resource": "*"},
        {"Effect": "Allow", "Action": "iam:PassRole", "Resource": execution_role,
         "Condition": {"StringEquals": {"iam:PassedToService": "cloudformation.amazonaws.com"}}},
        {"Effect": "Allow", "Action": "iam:ListRoles", "Resource": "*"},
        {"Effect": "Allow", "Action": "iam:GetRole", "Resource": execution_role},
        {"Effect": "Allow", "Action": ["logs:FilterLogEvents", "logs:GetLogEvents", "logs:DescribeLogStreams"],
         "Resource": [f"arn:aws:logs:{region}:{account}:log-group:/fidelity/{platform}/etp-{student}:*",
                      f"arn:aws:logs:{region}:{account}:log-group:/fidelity/{platform}/build-{student}:*"]},
    ]}


def package(args):
    output = args.output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    files = {str(p.relative_to(ROOT / "runtime")): p.read_bytes() for p in sorted((ROOT / "runtime").rglob("*"))
             if p.is_file() and "__pycache__" not in p.parts}
    files["tool-versions.json"] = json.dumps({"kubectl": args.kubectl}).encode()
    with zipfile.ZipFile(output / "runtime.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            archive.writestr("runtime/" + name, data)
    with tempfile.TemporaryDirectory() as directory:
        deps = Path(directory)
        subprocess.run([sys.executable, "-m", "pip", "install", "--platform", "manylinux2014_x86_64",
                        "--python-version", "3.12", "--implementation", "cp", "--only-binary=:all:",
                        "--target", str(deps), "-r", str(ROOT / "runtime/requirements.txt")], check=True)
        for p in deps.rglob("*"):
            if p.is_file() and "__pycache__" not in p.parts:
                files[str(p.relative_to(deps))] = p.read_bytes()
    url = f"https://dl.k8s.io/release/{args.kubectl}/bin/linux/amd64/kubectl"
    files["bin/kubectl"] = checked(url, url + ".sha256")
    url = "https://get.helm.sh/helm-v3.19.0-linux-amd64.tar.gz"
    with tarfile.open(fileobj=io.BytesIO(checked(url, url + ".sha256sum"))) as archive:
        files["bin/helm"] = archive.extractfile("linux-amd64/helm").read()
    index = yaml.safe_load(fetch("https://aws.github.io/eks-charts/index.yaml"))
    chart = next(c for c in index["entries"]["aws-load-balancer-controller"] if c["version"] == "3.5.0")
    files["controller.tgz"] = fetch(urljoin("https://aws.github.io/eks-charts/", chart["urls"][0]))
    if hashlib.sha256(files["controller.tgz"]).hexdigest() != chart["digest"]:
        raise ValueError("Controller chart checksum mismatch")
    files["rds-ca.pem"] = fetch("https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem")
    if sum(map(len, files.values())) > 250 * 1024 * 1024:
        raise ValueError("Setup package exceeds Lambda's uncompressed size limit")
    with zipfile.ZipFile(output / "setup.zip", "w", zipfile.ZIP_DEFLATED) as archive:
        for name, data in files.items():
            info = zipfile.ZipInfo(name)
            info.external_attr = (0o100755 if name.startswith("bin/") else 0o100644) << 16
            archive.writestr(info, data, compress_type=zipfile.ZIP_DEFLATED)
    digest = hashlib.sha256()
    for name in ("runtime.zip", "setup.zip"):
        digest.update((output / name).read_bytes())
    for name in ("shared.yaml", "learner.yaml"):
        digest.update((ROOT / name).read_bytes())
    prefix = "kits/" + digest.hexdigest()[:16]
    for name in ("shared.yaml", "learner.yaml"):
        template = yaml.safe_load((ROOT / name).read_text())
        template["Parameters"]["PlatformName"]["Default"] = args.platform
        if name == "shared.yaml":
            template["Parameters"]["AssetBucket"]["Default"] = args.bucket
            template["Parameters"]["AssetPrefix"]["Default"] = prefix
        (output / name).write_text(yaml.safe_dump(template, sort_keys=False, width=110))
    if args.upload:
        client = boto3.client("s3", region_name=args.region)
        for name in ("runtime.zip", "setup.zip", "shared.yaml", "learner.yaml"):
            client.upload_file(str(output / name), args.bucket, prefix + "/" + name)
    manifest = {"AssetBucket": args.bucket, "AssetPrefix": prefix, "Region": args.region,
                "PlatformName": args.platform,
                "LearnerTemplateUrl": f"https://{args.bucket}.s3.{args.region}.amazonaws.com/{prefix}/learner.yaml"}
    (output / "manifest.json").write_text(json.dumps(manifest, indent=2) + "\n")
    print(json.dumps(manifest, indent=2))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--bucket", required=True)
    parser.add_argument("--region", required=True)
    parser.add_argument("--platform", required=True)
    parser.add_argument("--kubectl", required=True, help="Exact compatible version, for example v1.34.1")
    parser.add_argument("--output", type=Path, default=ROOT / "build")
    parser.add_argument("--upload", action="store_true")
    package(parser.parse_args())
