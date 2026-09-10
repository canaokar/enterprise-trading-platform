# Deployment

**Engineering prepares the shared platform. Each graduate launches their AWS resources and deploys through Jenkins.** Plan for 143 separate environments, even when students share a group repository.

| Owner | Responsibility |
|---|---|
| Engineering | Shared CFT, EKS setup, Jenkins/JFrog, AWS access and infrastructure support |
| Graduate | Learner CFT, GitHub changes, Jenkins builds and application demonstration |
| Instructor | Guide the exercise, help with build errors and assess the result |

## Part 1: engineering

Run [shared.yaml](shared.yaml) once per regional cohort. It creates the VPC, EKS cluster and workers, shared RDS PostgreSQL, ALBs, ACM certificate and logging permissions.

Use an existing Jenkins and licensed JFrog service. Configure EKS and the Jenkins jobs before class. CloudFormation provisions AWS resources; Jenkins handles the database and Kubernetes application setup.

```bash
cp deploy/shared.example.json deploy/shared.local.json
# Fill in the account, domain and supported EKS/PostgreSQL versions.
aws cloudformation deploy --region ap-south-1 \
  --stack-name fidelity-india-shared --template-file deploy/shared.yaml \
  --parameter-overrides file://deploy/shared.local.json --capabilities CAPABILITY_IAM
```

Using the engineering role supplied as `PlatformAdminRoleArn`, install the shared Kubernetes components. Set `VPC_ID` from the stack output.

```bash
export PLATFORM=fidelity-india AWS_REGION=ap-south-1 VPC_ID=vpc-REPLACE
aws eks update-kubeconfig --name "$PLATFORM" --region "$AWS_REGION"
helm repo add eks https://aws.github.io/eks-charts
helm upgrade --install aws-load-balancer-controller eks/aws-load-balancer-controller \
  --namespace kube-system --version 3.5.0 \
  --set clusterName="$PLATFORM",region="$AWS_REGION",vpcId="$VPC_ID" \
  --set serviceAccount.name=aws-load-balancer-controller \
  --set enableServiceMutatorWebhook=false,enableBackendSecurityGroup=false \
  --set enableShield=false,enableWaf=false,enableWafv2=false --wait
envsubst '$PLATFORM $AWS_REGION' < deploy/platform.yaml | kubectl apply -f -
kubectl rollout status daemonset/fluent-bit -n amazon-cloudwatch
```

Configure one job per student from [Jenkinsfile](Jenkinsfile), named `<platform>-s001`, and connect it to the student's GitHub repository. Keep this pipeline definition under engineering control. Students get read/build access.

The pipeline uses the `platform` agent for [prepare.py](prepare.py), then the student's isolated agent for their code. Preparation creates the namespace, database/user, credentials, volumes and target bindings. It is safe to rerun. No student code runs on the platform agent.

The platform agent needs the engineering EKS role, CloudFormation read access and access to the platform's database secrets. Student agents need permission to assume only their own `ReleaseRoleArn`. Give each job JFrog credentials restricted to its image path. Attach the shared stack's `JenkinsSecurityGroupId` to agents in its VPC.

Install the approved `deploy/` directory at `/opt/fidelity/deploy` on the agents. Create `/opt/fidelity/.venv` from `requirements.txt` and save the [RDS CA bundle](https://truststore.pki.rds.amazonaws.com/global/global-bundle.pem) at `/opt/fidelity/rds-ca.pem`. Build agents need Java 21/Maven, Node 22.12+, Python 3.12+, Docker, AWS CLI, jq, kubectl and Helm 3.

Give each student an AWS login restricted to their assigned stack and the published learner template. Prefill its platform, ALB group, listener slot and Jenkins agent role. Assign 30 students per ALB: A/1 through A/30, then B/1, and so on. Five ALBs support 143 students with three target groups each. [AWS ALB limits](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-limits.html).

The two-worker default is for a pilot. Engineering must size workers, RDS and concurrent Jenkins builds from a measured class load. Test two students end to end, including separation between their data and resources, before handing the exercise to instructors.

## Part 2: graduates

1. Open the supplied [learner CFT](learner.yaml). Use your assigned stack name, such as `s001`, and the values supplied by engineering. Create the stack.
2. After `CREATE_COMPLETE`, open its `JenkinsUrl` output and select **Build Now**.
3. Wait for a successful build, then open `FrontendUrl`. Demonstrate login, an executed order and persisted data.
4. Push changes to your configured GitHub branch. Jenkins checks for changes every two minutes and deploys successful builds.

| Learner CFT creates | Jenkins deploys |
|---|---|
| Private S3 bucket and CloudFront | Production Angular build |
| Secrets and release permissions | Student database/user and schema on shared RDS |
| Target groups, HTTPS routes and DNS | Trade REST API, Trade Executor, Auth and Analytics in the student's namespace |
| CloudWatch log group | Kafka and persistent application storage |

The repository must provide the four Docker build contexts, Angular build and ordered `infra/postgres/*.sql` migrations used by the pipeline. Add new migrations instead of changing applied ones.

## Instructor operations

For stack errors, collect the stack name and failed CloudFormation event for engineering. For code errors, inspect the Jenkins console with the student, fix the code and rebuild. Infrastructure failures across several students go to engineering.

Engineering handles final cleanup: stop the job, delete its target bindings and namespace, drop its database/user, then delete the learner stack. Buckets and secrets are retained for assessment; engineering removes them afterwards, along with the student's JFrog images and job. Delete shared infrastructure last. RDS requires `ProtectDatabase=false` and leaves a final snapshot.

Local template and chart checks do not replace the AWS pilot.
