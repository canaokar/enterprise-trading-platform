**CloudFormation deployment kit**

This kit provisions a shared regional platform and one environment per group or student. Use `g001` to `g060` for group deployments. Use `s001` to `s143` only if separate student environments are required.

The templates and supporting manifests have local validation. They have not been deployed to AWS. Complete the pilot checks below before handing the lab to instructors.

| File | Owner and purpose |
|---|---|
| [shared.yaml](shared.yaml) | Engineering: VPC, two public and two private subnets, one NAT gateway, S3 endpoint, EKS, fixed worker pool, EBS driver, shared RDS, HTTPS ALBs and ACM |
| [student.yaml](student.yaml) | Trusted provisioning job: group S3/CloudFront, Secrets Manager secrets, target groups, DNS, CloudWatch logs/alarm and a scoped release role |
| [bootstrap_platform.py](bootstrap_platform.py) | Engineering: target-binding controller, encrypted gp3 storage class, service admission policy and Fluent Bit |
| [environment.py](environment.py) | Engineering: parameter generation, group database/user, migrations, namespace, permissions, isolation, volumes and secret synchronisation |
| [trading Helm chart](../helm/trading/Chart.yaml) | Graduate release: four application containers, Kafka and topic initialisation |
| [release.py](release.py) | Jenkins: assume the group role, deploy images, upload Angular, invalidate CloudFront and check HTTP endpoints |
| [Jenkinsfile.example](../Jenkinsfile.example) | Starting pipeline for one group, with GitHub checkout, tests, JFrog publication and release |

The shared platform defaults to two ALBs, each with 30 environment slots. Each slot consumes three target groups and listener priorities ending in 1, 2 and 3. Keep the slot assignment in the instructor roster.

CloudFormation owns the ALBs, listeners, rules and target groups. Kubernetes only registers pod IPs through instructor-owned TargetGroupBindings. Learners cannot change bindings, ingress, namespace policies or shared infrastructure.

**Prerequisites**

- Use a dedicated training account and an engineering IAM role. The role must be able to provision the resource types in these templates.
- Provide a delegated public Route 53 hosted zone in that account. An ACM certificate cannot validate until DNS delegation works.
- Select supported EKS and PostgreSQL 16 versions in the target region. Supply exact versions in the parameters file.
- Install AWS CLI v2, Python 3.12+, kubectl and Helm 3.19 or a compatible Helm 3 version.
- Prepare an existing licensed JFrog registry and a reachable Jenkins service. The optional EC2 resource requires a prebuilt Jenkins AMI; it does not install Jenkins, agents or Artifactory.
- Run database bootstrap from a VPC-connected engineering host. The optional Jenkins host can provide that network location through SSM, using the engineer's own temporary AWS credentials.
- Run release agents inside the VPC or over approved connectivity. Give each group an isolated agent identity and group-scoped JFrog credentials. Do not run student builds on the Jenkins controller or mount the application nodes' Docker socket.

The optional Jenkins host is private, has no inbound rules and carries only SSM permissions. Use SSM port forwarding for administration. An existing webhook-capable Jenkins service is preferable. For a private controller, use SCM polling until an approved webhook path is configured.

**1. Provision the shared stack**

Run from the repository root with engineering credentials. The commands below create chargeable AWS resources when executed.

```bash
python3 -m venv deploy/cloudformation/.venv
deploy/cloudformation/.venv/bin/pip install -r deploy/cloudformation/requirements.txt

aws eks describe-cluster-versions --region ap-south-1
aws rds describe-db-engine-versions --engine postgres --region ap-south-1 \
  --query "DBEngineVersions[?starts_with(EngineVersion, '16.')].EngineVersion"

cp deploy/cloudformation/parameters/shared.example.json deploy/cloudformation/parameters/shared.local.json
```

Replace the example values. Use a narrow engineering/VPN source CIDR for `ApiAccessCidr`. The worker default is pilot capacity, not capacity for 60 groups.

```bash
aws cloudformation deploy --region ap-south-1 \
  --stack-name fidelity-india-shared \
  --template-file deploy/cloudformation/shared.yaml \
  --parameter-overrides file://deploy/cloudformation/parameters/shared.local.json \
  --capabilities CAPABILITY_IAM --no-fail-on-empty-changeset

aws eks update-kubeconfig --region ap-south-1 --name fidelity-india

deploy/cloudformation/.venv/bin/python deploy/cloudformation/bootstrap_platform.py \
  --region ap-south-1 --shared-stack fidelity-india-shared
```

The EKS access entry is for `PlatformAdminRoleArn`, not automatically for whoever creates the stack. Use that role for kubectl. EKS version changes require compatible add-on versions; inspect installed versions and pin the tested lab versions before delivery.

The bootstrap installs AWS Load Balancer Controller chart `3.5.0` and AWS for Fluent Bit `3.2.1`. Validate them with the selected EKS version during the pilot. Workload logs go only to pre-created group log groups.

**2. Provision one group or student environment**

First create or select that group's isolated Jenkins agent IAM role. It must not be a role that all student jobs can use. Existing SSO users and Jenkins accounts are organisation-specific and are not created by these templates.

```bash
deploy/cloudformation/.venv/bin/python deploy/cloudformation/environment.py \
  --region ap-south-1 --shared-stack fidelity-india-shared parameters \
  --environment g001 --alb A --slot 1 \
  --agent-role arn:aws:iam::123456789012:role/JenkinsAgentG001 \
  --output deploy/cloudformation/parameters/g001.local.json

aws cloudformation deploy --region ap-south-1 \
  --stack-name fidelity-india-g001 \
  --template-file deploy/cloudformation/student.yaml \
  --parameter-overrides file://deploy/cloudformation/parameters/g001.local.json \
  --capabilities CAPABILITY_IAM --no-fail-on-empty-changeset
```

Use slots 1 to 30 on ALB A, then slots 1 to 30 on ALB B. Reusing a slot on one listener fails. Use stack names under 50 characters so derived CloudFront names fit their limits.

Provisioning creates credentials, not a PostgreSQL database or Kubernetes namespace. Complete the next step from inside the VPC:

```bash
curl -fsSL https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem \
  -o /tmp/etp-rds-ca.pem

deploy/cloudformation/.venv/bin/python deploy/cloudformation/environment.py \
  --region ap-south-1 --shared-stack fidelity-india-shared bootstrap \
  --student-stack fidelity-india-g001 --rds-ca /tmp/etp-rds-ca.pem \
  --migration infra/postgres/01-schema.sql \
  --migration infra/postgres/02-seed.sql \
  --migration infra/postgres/03-extensions.sql \
  --output deploy/cloudformation/parameters/g001.outputs.local.json
```

The script creates a group database owner with no cluster administration privileges. All reference services use that group credential; database isolation is between groups. Analytics is not assigned a separate read-only database role in this starter.

Migrations run in order, with a checksum ledger. Unchanged files are skipped. Editing an applied migration fails. Pass each group's own migration files when onboarding student implementations. Run later schema changes as an instructor-controlled migration job before releasing compatible images.

Secrets remain in Secrets Manager and are copied into the group's Kubernetes Secret through stdin. Output JSON contains resource identifiers and URLs, not credentials. This deliberately avoids a secret operator. After rotating a secret, rerun bootstrap and restart the affected deployments.

Create a `jfrog-pull` image-pull secret in the namespace using that group's read-only registry credential. Supply it through the approved credential-management workflow. Do not put registry passwords in values files or command history.

Grant the group's Jenkins agent role `sts:AssumeRole` on the exact `ReleaseRoleArn` from the output file. The target role also trusts that agent role. Give learners AWS console visibility through scoped SSO permission sets if required; do not share an AWS login.

**3. Run the graduate pipeline**

Copy the non-secret output file to `/opt/etp/g001.outputs.json` on the group's agent. Configure its Jenkins label, JFrog host, repository prefix and credential ID in the example Jenkinsfile.

Agents need Java 21/Maven, a Node version supported by Angular 21, Python 3.12+, AWS CLI v2, kubectl, Helm 3 and an isolated Docker builder. The example builds Linux AMD64 images for the selected EKS nodes.

Configure GitHub checkout and webhook/polling in Jenkins. Branch/PR builds run tests. The example publishes and releases only from `main`. Restrict each credential to its group's Jenkins folder and avoid privileged credentials in untrusted PR jobs.

The release role can upload this frontend, invalidate its distribution, read its logs and deploy into its namespace. It cannot update the CloudFormation stack, create IAM roles or read the RDS administrator secret.

CloudFormation changes therefore run in a separate trusted provisioning job. Graduates can request approved parameter changes through that job. Do not grant administrative stack execution to a student-editable Jenkinsfile.

This refines the earlier pipeline outline: infrastructure provisioning is a controlled stage outside the application Jenkinsfile. Individual release assessment remains unchanged.

Application images must use a Git commit tag or digest. The chart uses pilot memory settings and three database connections per service. It keeps Analytics at one replica with a `Recreate` strategy. The default quote mode is `fixture`.

The pipeline smoke checks HTTP availability. The final assessment must also demonstrate login, order execution, persistence, CloudWatch log delivery and a previous release. Public analytics routing permits only `/` and `/index.html`, protecting the colocated DuckDB file from direct download. Use synthetic training data.

**Instructor operations**

| Action | Procedure |
|---|---|
| Deploy | Run the group's Jenkins job. Same-group releases are serialised. Limit the shared agent pool to three to five concurrent builds initially. |
| Roll back | Re-run a previously successful commit with its archived frontend and image versions. Helm rollback alone does not restore S3. Database rollback is separate. |
| Stop group | Scale its four Deployments and Kafka StatefulSet to zero. Keep the namespace, database and PVCs. Stop its Jenkins job before changing replica counts. |
| Start group | Run the group's successful release again. Its existing database and volumes remain available. |
| Rotate secrets | Rerun bootstrap with unchanged migrations, then restart application Deployments. The secret sync is not automatic. |
| Diagnose | Check CloudFormation events, pod status/events and group logs. Escalate shared RDS/EKS/registry failures to the remote platform owner. |

Kafka and Analytics volumes are outside the Helm release. Uninstalling the chart leaves them intact. Namespace deletion deletes those PVCs and their EBS volumes.

For final cleanup, uninstall each application and delete instructor-owned TargetGroupBindings before deleting its CloudFormation stack. Verify target deregistration, then delete the namespace only after accepting data loss. Remove application agents and credentials separately.

Student stacks retain S3 buckets and Secrets Manager secrets. Shared RDS deletion requires a reviewed update setting `ProtectDatabase=false`, and creates a final snapshot. The optional Jenkins root volume is retained. Inventory and remove retained resources after assessment; they continue to incur charges. Retained secret names must be resolved before recreating an environment with the same ID.

**Validation and pilot gate**

```bash
deploy/cloudformation/.venv/bin/cfn-lint \
  deploy/cloudformation/shared.yaml deploy/cloudformation/student.yaml
deploy/cloudformation/.venv/bin/python -m unittest discover -s deploy/cloudformation/tests
```

Local validation covers template structure, rendered Kubernetes resources and isolation contracts. It cannot establish account quotas, live IAM decisions, DNS delegation, image startup, database compatibility or cohort capacity.

Before teaching, deploy two groups and verify that one cannot alter the other's resources, bindings or data. Test a cold start, a release, secret refresh and a stop/start cycle. Then test the planned simultaneous group count and build concurrency. Record tested EKS/add-on/chart versions and the revised AWS cost estimate.

The setup requires a named remote platform engineer during class. It removes routine infrastructure work from instructors; it does not remove platform support.

Technical references: [EKS CloudFormation integration](https://docs.aws.amazon.com/eks/latest/userguide/creating-resources-with-cloudformation.html), [TargetGroupBinding ownership](https://kubernetes-sigs.github.io/aws-load-balancer-controller/latest/guide/targetgroupbinding/targetgroupbinding/), [ALB quotas](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-limits.html), [EKS tenant isolation](https://docs.aws.amazon.com/eks/latest/best-practices/tenant-isolation.html).
