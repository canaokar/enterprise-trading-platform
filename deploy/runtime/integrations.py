"""Engineering-owned Jenkins and JFrog integration. Credentials never reach job XML."""
import base64
import json
import urllib.error
import urllib.parse
import urllib.request
import xml.etree.ElementTree as ET


class Api:
    def __init__(self, url, authorization):
        parsed = urllib.parse.urlsplit(url)
        if parsed.scheme != "https" or not parsed.netloc or parsed.username or parsed.query or parsed.fragment:
            raise ValueError("Integration URLs must be plain HTTPS URLs")
        self.url = url.rstrip("/")
        self.authorization = authorization

    def request(self, path, method="GET", data=None, content_type="application/json", missing=False):
        if not path.startswith("/") or path.startswith("//"):
            raise ValueError("API paths must be relative to the configured service")
        if data is not None and not isinstance(data, bytes):
            data = json.dumps(data).encode()
        request = urllib.request.Request(self.url + path, data=data, method=method,
                                         headers={"Authorization": self.authorization, "Content-Type": content_type})
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                body = response.read()
                return (json.loads(body) if body and "json" in response.headers.get("Content-Type", "") else body,
                        response.headers)
        except urllib.error.HTTPError as error:
            if missing and error.code == 404:
                return None, {}
            raise RuntimeError(f"Integration {method} request failed with HTTP {error.code}") from None


def jenkins(secret):
    token = base64.b64encode((secret["username"] + ":" + secret["apiToken"]).encode()).decode()
    return Api(secret["url"], "Basic " + token)


def jfrog(secret):
    return Api(secret["url"], "Bearer " + secret["token"])


def registry_permission(name, repository, platform, student, username):
    return {"name": name, "repo": {"repositories": [repository],
            "include-patterns": [f"{platform}/{student}/**"], "exclude-patterns": [],
            "actions": {"users": {username: ["read", "write", "annotate"]}, "groups": {}}}}


def provision_registry(api, configuration, credential, platform, student):
    name = credential["username"]
    path = "/access/api/v2/users/" + name
    existing, _ = api.request(path, missing=True)
    if existing is None:
        api.request("/access/api/v2/users", "POST", {
            "username": name, "password": credential["password"], "email": name + "@example.invalid",
            "admin": False, "groups": [], "profile_updatable": False,
            "internal_password_disabled": False, "disable_ui_access": True,
        })
    else:
        if existing.get("admin") or existing.get("groups"):
            raise ValueError("Lab registry user has unexpected inherited permissions")
    api.request("/artifactory/api/v2/security/permissions/" + name, "PUT",
                registry_permission(name, configuration["dockerRepository"], platform, student, name))


def delete_registry(api, configuration, platform, student):
    name = platform + "-" + student
    api.request("/access/api/v2/users/" + name, "DELETE", missing=True)
    api.request("/artifactory/api/v2/security/permissions/" + name, "DELETE", missing=True)
    api.request(f"/artifactory/{configuration['dockerRepository']}/{platform}/{student}", "DELETE", missing=True)


def job_xml(config, student, project, repository, branch, owner):
    # Literal quoting keeps branch/repository strings out of executable Groovy expressions.
    literal = json.dumps
    script = f"""pipeline {{
  agent {{ label {literal(config['JenkinsCheckoutLabel'])} }}
  options {{ disableConcurrentBuilds(); timestamps(); timeout(time: 35, unit: 'MINUTES'); buildDiscarder(logRotator(numToKeepStr: '10')) }}
  triggers {{ pollSCM('H/2 * * * *') }}
  stages {{
    stage('GitHub checkout') {{
      steps {{
        checkout([$class: 'GitSCM', branches: [[name: {literal('*/' + branch)}]],
          userRemoteConfigs: [[url: {literal(repository)}, credentialsId: {literal(config['JenkinsGitCredentialId'])}]]])
        script {{ env.RELEASE_COMMIT = sh(script: 'git rev-parse HEAD', returnStdout: true).trim() }}
      }}
    }}
    stage('Test, publish and deploy') {{
      steps {{
        awsCodeBuild projectName: {literal(project)}, region: {literal(config['Region'])},
          credentialsType: 'keys', sourceControlType: 'project',
          secondarySourcesVersionOverride: '[{{"sourceIdentifier":"application","sourceVersion":"' + env.RELEASE_COMMIT + '"}}]'
      }}
    }}
  }}
}}
"""
    root = ET.Element("flow-definition", {"plugin": "workflow-job"})
    ET.SubElement(root, "description").text = "Managed by Fidelity CloudFormation. Owner: " + owner
    ET.SubElement(root, "keepDependencies").text = "false"
    properties = ET.SubElement(root, "properties")
    matrix = ET.SubElement(properties, "hudson.security.AuthorizationMatrixProperty", {"plugin": "matrix-auth"})
    ET.SubElement(matrix, "inheritanceStrategy", {"class": "org.jenkinsci.plugins.matrixauth.inheritance.InheritParentStrategy"})
    for permission in ("hudson.model.Item.Read", "hudson.model.Item.Build", "hudson.model.Item.Cancel"):
        ET.SubElement(matrix, "permission").text = "USER:" + permission + ":" + config["PlatformName"] + "-" + student
    definition = ET.SubElement(root, "definition", {"class": "org.jenkinsci.plugins.workflow.cps.CpsFlowDefinition", "plugin": "workflow-cps"})
    ET.SubElement(definition, "script").text = script
    ET.SubElement(definition, "sandbox").text = "true"
    ET.SubElement(root, "triggers")
    ET.SubElement(root, "disabled").text = "false"
    return ET.tostring(root, encoding="utf-8")


def put_job(api, config, student, project, repository, branch, owner):
    name = config["PlatformName"] + "-" + student
    path = "/job/" + name
    existing, _ = api.request(path + "/api/json?tree=description", missing=True)
    if existing is not None and existing.get("description") != "Managed by Fidelity CloudFormation. Owner: " + owner:
        raise ValueError("Jenkins job belongs to a different stack")
    xml = job_xml(config, student, project, repository, branch, owner)
    api.request(path + "/config.xml" if existing is not None else "/createItem?name=" + name,
                "POST", xml, "application/xml")
    return api.url + path + "/"


def stop_job(api, job_name, owner):
    path = "/job/" + job_name
    job, _ = api.request(path + "/api/json?tree=description,builds[number,building]", missing=True)
    if job is None:
        return
    if job.get("description") != "Managed by Fidelity CloudFormation. Owner: " + owner:
        raise ValueError("Jenkins job belongs to a different stack")
    api.request(path + "/disable", "POST", b"")
    queue, _ = api.request("/queue/api/json?tree=items[id,task[name]]")
    for item in queue["items"]:
        if item["task"]["name"] == job_name:
            api.request("/queue/cancelItem?id=" + str(int(item["id"])), "POST", b"")
    for build in job.get("builds", []):
        if build.get("building"):
            api.request(path + "/" + str(int(build["number"])) + "/stop", "POST", b"", missing=True)


def delete_job(api, job_name, owner):
    stop_job(api, job_name, owner)
    api.request("/job/" + job_name + "/doDelete", "POST", b"", missing=True)
