"""Install verified Linux tooling inside disposable CodeBuild workers."""
import hashlib
import json
from pathlib import Path
import re
import subprocess
import tarfile
import urllib.request


def download(url):
    with urllib.request.urlopen(url, timeout=60) as response:
        return response.read()


def verified(url, checksum_url):
    data = download(url)
    checksum = download(checksum_url).decode().split()[0]
    if hashlib.sha256(data).hexdigest() != checksum:
        raise RuntimeError("Tool checksum mismatch")
    return data


def main():
    version = json.loads((Path(__file__).parent / "tool-versions.json").read_text())["kubectl"]
    if not re.fullmatch(r"v1\.[0-9]+\.[0-9]+", version):
        raise ValueError("Invalid kubectl version")
    url = f"https://dl.k8s.io/release/{version}/bin/linux/amd64/kubectl"
    target = Path("/usr/local/bin/kubectl")
    target.write_bytes(verified(url, url + ".sha256"))
    target.chmod(0o755)
    url = "https://get.helm.sh/helm-v3.19.0-linux-amd64.tar.gz"
    archive = Path("/tmp/helm.tar.gz")
    archive.write_bytes(verified(url, url + ".sha256sum"))
    with tarfile.open(archive) as package:
        binary = package.extractfile("linux-amd64/helm")
        target = Path("/usr/local/bin/helm")
        target.write_bytes(binary.read())
        target.chmod(0o755)
    Path("/tmp/rds-ca.pem").write_bytes(download("https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem"))
    subprocess.run(["helm", "version", "--short"], check=True)


if __name__ == "__main__":
    main()
