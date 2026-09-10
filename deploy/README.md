# Deployment

Engineering launches the shared stack. Each graduate launches a learner stack, opens Jenkins and selects **Build Now**. Later GitHub changes trigger builds automatically.

EKS and RDS remain shared. Each graduate gets their own application containers, Kafka, database, secrets and frontend.

## 1. Engineering

Use an existing Jenkins and JFrog service. Prepare these once for the cohort:

- Jenkins plugins: Pipeline, Git, Folders, Credentials Binding, Pipeline Utility Steps, Pipeline: AWS Steps and Matrix Authorization Strategy. Use project-based matrix authorisation. Students need global Overall/Read and Job/Read; the generated jobs grant Build/Cancel to their assigned `s001`-style login. Instructors receive access to all cohort jobs. Students must not have Configure or Replay access.
- One trusted agent labelled `platform-<PlatformName>`, and a pool labelled `training-build-<PlatformName>`. Build agents have one executor, are discarded after each build and have no base AWS credentials. The controller assumes the student's release role and passes temporary credentials to the build. Leave Pipeline: AWS Steps' "Retrieve credentials from node" disabled.
- The controller and platform agent use `PlatformAdminRoleArn`. It needs EKS access, CloudFormation read access and read access to the lab's database/JWT secrets. Agents run in the training VPC with its `JenkinsSecurityGroupId` attached.
- Jenkins credentials: `github-read` for repository access, and `jfrog-s001` etc. scoped to `<JFrogRepository>/<PlatformName>/s001/*`. Store a Jenkins service user's `username` and `apiToken` in Secrets Manager; supply its ARN to the shared CFT. That service user needs permission to create/configure cohort jobs and their region folder.

Install the approved `deploy/` directory at `/opt/fidelity/deploy` on both agent types. Build agents need Java 21/Maven, Node 22.12+, Python 3.12+, Docker, AWS CLI, jq, kubectl and Helm 3. The platform agent needs AWS CLI and kubectl. Both agent types need the Python environment and database certificate:

```bash
python3 -m venv /opt/fidelity/.venv
/opt/fidelity/.venv/bin/pip install boto3==1.43.89 'psycopg[binary]==3.3.5' PyYAML==6.0.3
curl -fsSL https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem -o /opt/fidelity/rds-ca.pem
```

Upload [shared.yaml](shared.yaml) in CloudFormation. Name the stack `<PlatformName>-shared`, for example `fidelity-india-shared`. Supply the domain, hosted zone, supported EKS/PostgreSQL versions, Jenkins/JFrog details and student range. Use different platform names and non-overlapping student ranges for India and the US.

The stack creates VPC, EKS, RDS, ALBs, certificate and logs. Its setup instance installs the EKS components and creates every student Jenkins job from the same [Jenkinsfile](Jenkinsfile). Stack creation waits for that setup to finish. Engineering does not install controllers by hand or edit a pipeline per student.

Assign student IDs `s001` to `s143` and restricted AWS logins. Give each student their platform name, ALB group and listener slot. Allow 30 students per ALB: A/1 to A/30, then B/1, and so on. Set `AlbCount` accordingly. The two-worker default is for a pilot; size workers, RDS and build concurrency from measured load.

Run two student deployments before class. Give instructors the working URLs and the steps below.

## 2. Graduates

1. Upload [learner.yaml](learner.yaml) in CloudFormation. Use your assigned student ID as the stack name. Enter the supplied platform/ALB values, your group's GitHub repository URL and branch.
2. Wait for `CREATE_COMPLETE`. Open the `JenkinsUrl` output and select **Build Now**.
3. When the build succeeds, open `FrontendUrl`. Demonstrate login, an order and persisted data.
4. Push a change to your branch. Jenkins checks GitHub every two minutes and deploys successful builds.

| Learner CFT creates | Jenkins prepares and deploys |
|---|---|
| S3 and CloudFront | Production Angular build |
| Secrets and release role | Student database/user and SQL schema on shared RDS |
| HTTPS routes and logs | Trade REST API, Trade Executor, Auth, Analytics and Kafka in the student's EKS namespace |

The repository must contain the four Docker build contexts, `ui/` and ordered `infra/postgres/*.sql` migrations used by the pipeline. Add migrations instead of editing applied ones.

## Instructor support and cleanup

For a stack failure, send engineering the failed CloudFormation event. For a build failure, inspect the Jenkins console with the student, fix the code and rebuild. Shared infrastructure failures go to engineering.

Engineering stops the jobs, deletes student target bindings and namespaces, drops their databases/users, then deletes learner stacks. Remove retained S3 buckets, secrets, registry images and Jenkins jobs after assessment. Delete shared infrastructure last. RDS needs `ProtectDatabase=false` and retains a final snapshot.

The setup instance runs during stack creation. Later EKS upgrades and Jenkins account/credential changes remain engineering work. Local checks have passed; a live AWS/Jenkins pilot is still required.
