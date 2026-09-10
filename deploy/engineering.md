# Engineering setup

Use a dedicated training account per regional cohort. Keep learner stack names local to that account and region: `s001` through the cohort's last student. The shared platform name distinguishes regional resources.

## Prepare the integrations

These are engineering prerequisites, completed before handing over the learner template.

| Input | Requirement |
|---|---|
| AWS and DNS | Training account, delegated public Route 53 zone, narrow engineering/VPN CIDR and private S3 artefact bucket in the deployment region |
| Jenkins | Existing HTTPS service reachable from the new VPC, an API service account, GitHub checkout credentials and a lightweight checkout agent |
| Jenkins plugins | Pipeline, Declarative Pipeline, Git, AWS CodeBuild, Timestamper and Matrix Authorization Strategy |
| Jenkins permissions | Project-based Matrix Authorization Strategy. Engineering administers jobs; instructors can read/build/cancel. Give students global Overall/Read only. |
| Jenkins AWS identity | Existing same-account IAM role available through the CodeBuild plugin's default credential chain. The shared CFT attaches its build permissions. |
| JFrog | Existing licensed Artifactory with a local Docker repository and repository-path Docker access. No anonymous access or default groups that grant cohort-wide write access. |
| GitHub | An authorised, `AVAILABLE` AWS CodeConnections connection for the cohort repositories |

Jenkins uses disposable CodeBuild workers to run tests, Docker builds and releases. This avoids maintaining 143 build agents. Student code never runs on the Jenkins controller or under the setup function's permissions.

Create two Secrets Manager secrets using the console or your credential-management process. Do not put values in parameter files.

```json
{"url":"https://jenkins.example.com","username":"lab-automation","apiToken":"..."}
```

```json
{"url":"https://example.jfrog.io","token":"...","registryHost":"example.jfrog.io","dockerRepository":"docker-local"}
```

The Jenkins account needs job administration and queue access. The JFrog token needs lab user, permission and image administration. Setup creates a restricted registry user and path for each student. Validate these APIs against your JFrog installation during the pilot.

Jenkins student usernames must be `<platform>-<student>`, for example `fidelity-india-s001`. Connect those identities through your existing login system. Jobs grant their student read/build/cancel access; students cannot configure or replay pipelines.

## Launch the shared stack

Install Python 3.12+, AWS CLI v2 and the packaging dependencies on an engineering machine. Packaging downloads the pinned setup tools and uploads the release assets. It creates no running infrastructure.

```bash
python3 -m venv deploy/.venv
deploy/.venv/bin/pip install -r deploy/runtime/requirements.txt

deploy/.venv/bin/python deploy/package.py \
  --bucket YOUR-PRIVATE-ARTEFACT-BUCKET --region ap-south-1 \
  --platform fidelity-india --kubectl v1.34.1 --upload

cp deploy/shared.example.json deploy/shared.local.json
```

Replace every example value. Select EKS and PostgreSQL versions available in the target region. Match the packaged kubectl version to EKS. The example below is pilot-sized; it does not support 143 active students.

```bash
aws cloudformation deploy --region ap-south-1 \
  --stack-name fidelity-india-shared \
  --template-file deploy/build/shared.yaml \
  --parameter-overrides file://deploy/shared.local.json \
  --capabilities CAPABILITY_NAMED_IAM

deploy/.venv/bin/python deploy/handover.py \
  --region ap-south-1 --shared-stack fidelity-india-shared
```

Apply the generated `deploy/build/handover/sNNN.json` policies to the matching individual AWS identities. Use them without broader developer/admin policies. Give instructors `students.csv` and the [learner guide](README.md).

The policies restrict stack creation to the published learner template, assigned stack name and supplied execution role. Keep release assets read-only for students. The CloudFormation role provisions resources on their behalf; students do not receive that role's AWS permissions directly.

## Pilot and capacity

Run the exercise with two fresh student identities. Confirm creation, a successful Jenkins release, another GitHub push and deletion. Check that one student cannot build the other's job, modify the other's stack or access the other's database and registry path.

The repository must supply the four Docker build contexts, production Angular build, tests and ordered `infra/postgres/*.sql` migrations used by `runtime/build.py`. The reference branch supplies this contract. The regional teaching branches contain starter material; finished student repositories must implement it.

Jenkins applies SQL with the student's database credentials. Applied migrations use a checksum ledger. Add new migration files instead of editing applied ones. Use compatible schema changes; application rollback does not reverse database changes.

Use one ALB per 30 students: one for the pilot, five for all 143 in one region. Each student consumes three target groups; AWS limits an ALB to 100. [ALB quotas](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-limits.html).

Set `StudentCount`, `AlbCount` and `WorkerCount` together before class. Measure JVM memory, CPU, pod capacity and RDS connections under concurrent startup. Check EC2, EKS access entry, CodeBuild concurrency, CloudFront and load balancer quotas. Keep three concurrent releases initially. A named platform engineer should be reachable during class.

## Operations

Use CloudFormation Events for provisioning failures, Jenkins for build failures and `/fidelity/<platform>/...` CloudWatch logs for application failures. Setup failures appear under `/aws/lambda/<platform>-setup`.

On a failed creation, let rollback finish. Delete the failed learner stack before reusing its ID. If deletion fails, fix the reported dependency and retry deletion. Do not force-remove Kubernetes finalisers or manually delete shared resources.

Publish a new kit prefix for infrastructure changes. Engineering performs template updates; routine student releases remain GitHub pushes. Pin the kit used for the classroom and avoid platform updates during teaching.

Delete learner stacks after assessment. Their resources have no retention policy. Delete the shared stack last, after setting `ProtectDatabase=false` through a reviewed update. Shared RDS leaves a final snapshot; artefact uploads and existing Jenkins/JFrog remain engineering-owned and can still incur charges.

## Local checks

```bash
deploy/.venv/bin/pip install -r deploy/tests/requirements.txt
deploy/.venv/bin/cfn-lint deploy/shared.yaml deploy/learner.yaml
deploy/.venv/bin/python -m unittest discover -s deploy/tests
```

The setup function handles operations that CloudFormation cannot express natively: namespaces, database users and Jenkins jobs. It triggers the initial build without waiting for it. [CloudFormation custom resources](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-custom-resources.html).

Integration references: [Jenkins CodeBuild plugin](https://github.com/jenkinsci/aws-codebuild-plugin), [JFrog permission targets](https://docs.jfrog.com/administration/reference/createorreplacepermissiontargetv2), [CloudFormation access controls](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/control-access-with-iam.html).
