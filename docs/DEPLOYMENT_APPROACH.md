> Superseded by the [two-part deployment kit](../deploy/README.md). The current model gives each of 143 graduates a separate environment.

**Fidelity graduate deployment approach**

Status: proposal for engineering and delivery review. Updated 5 September 2026.

**Recommendation**

Provide 50 to 60 group environments on shared AWS infrastructure. Assess all 143 participants through individual Jenkins releases into their group's environment.

Each participant commits a change, runs a release, demonstrates the application, inspects its logs and deploys a previous working version. Serialize releases within each group.

Fidelity must accept this definition of individual deployment. If every participant needs a separate environment, shared EKS can still support that model, but capacity must cover 143 application copies.

Use the same templates for India and US. Default to one training account, EKS cluster and shared RDS instance per regional cohort. Share Jenkins and JFrog where existing access permits. Account access does not require an account per participant.

This expands the current curriculum. The branch deployment briefs cover Angular on S3/CloudFront, with backends running locally. [Decision 4](DECISIONS.md) excludes much of the requested cloud stack. Update those briefs and assessments before delivery.

**What we prepare and what graduates deploy**

| Component | Engineering prepares before training | Graduates own during training |
|---|---|---|
| AWS foundation | CloudFormation for VPC, subnets, security groups, routing, EKS, managed worker nodes, shared ALBs, DNS and ACM certificates | Explain the supplied architecture and template |
| Group access | Individual SSO access, group namespaces, scoped AWS and Kubernetes roles, network policies, quotas and container restrictions | Use their own identity and operate within their group |
| PostgreSQL | Shared RDS PostgreSQL, separate database and restricted user per group, credentials in Secrets Manager | Apply their schema, migrations and seed data through Jenkins |
| Kubernetes deployment | Tested Helm chart, storage configuration, health probes and centrally controlled ingress routing | Supply image versions and application settings; deploy their group release |
| Jenkins | Controller, isolated build agents, GitHub integration, group jobs, credentials and pipeline starter | Complete and maintain their repository's Jenkinsfile |
| JFrog | Shared Artifactory registry, group permissions and retention policy | Publish versioned images and build artefacts |
| Frontend | CloudFormation starter for private S3, origin access control and CloudFront | Create/update their group frontend stack and publish Angular through Jenkins |
| Secrets and monitoring | Group secrets, delivery to workloads and CloudWatch log collection | Reference secrets, inspect logs and configure a supplied alarm through the group template |
| Instructor operations | Deploy, Roll back and Stop/Start group actions; separate final cleanup job | Provide release evidence and explain failures |

Engineering owns shared infrastructure changes. Group pipelines use restricted execution roles and cannot modify another group's resources. Keep student builds away from platform administration credentials.

**What runs for each group**

| Workload | Deployment |
|---|---|
| Trade REST API | One container, including domain code and extension modules |
| Trade Executor | One container, including the market-data poller |
| Auth service | One container |
| Analytics | One container with persistent DuckDB storage |
| Kafka | One broker container with persistent storage |
| Angular | Production static build in S3 behind CloudFront |
| PostgreSQL | Group database inside the shared RDS instance |
| Initialisation | Short-lived database migration and Kafka topic creation jobs |

This is five long-running containers per group, or 250 to 300 workload pods if all groups run together. Platform components and temporary build/migration pods are additional.

Keep Kafka separate per group. This preserves the existing topic names and avoids cross-group event handling. Shared Kafka would need additional credential, topic and consumer-group isolation work.

Use one replica for each workload during this training. Give Kafka and Analytics separate persistent volumes. Deploy Analytics with a strategy that prevents two processes opening the same writable DuckDB file.

Expose the Trade REST API, Auth service and analytics report through shared HTTPS ingress. Configure Angular with the group's cloud endpoints and matching CORS settings. Use CloudFront's default HTTPS hostname for the frontend; custom CloudFront domains require their own certificate setup.

**Jenkins release flow**

1. A participant pushes to GitHub. Branch and pull request builds run checks.
2. A merge to the agreed deployment branch triggers Jenkins to check out that exact commit.
3. Jenkins runs Java, Node, Angular and Python checks, then builds production artefacts and container images.
4. Jenkins pushes images to JFrog using immutable commit identifiers.
5. Jenkins applies the group's CloudFormation template for frontend resources, log groups and alarms.
6. Jenkins runs initialisation/migrations and deploys the supplied Helm chart with the new images.
7. Jenkins uploads Angular to S3, invalidates CloudFront and runs login/order smoke tests.
8. Jenkins records the commit, image versions, deployment URL, results and participant evidence.

Keep the Jenkinsfile in GitHub. Jenkins reports build status back to GitHub; it does not need to push application code back. [Jenkins pipeline guidance](https://www.jenkins.io/doc/book/pipeline/jenkinsfile/).

Retain the previous working image versions. Rollback restores application versions, not database contents. Keep deployment-week schema changes backward compatible.

**Assessment of the engineer's estimate**

The shared-EKS direction agrees with this proposal. The two estimates compare different infrastructure ownership models, but both assume 143 application environments and 143 RDS instances.

| Scenario | Application environments | RDS instances | Weekly figure |
|---|---:|---:|---|
| Engineer option A: shared EKS | 143 | 143 | $2,218 supplied estimate, about $15.51 per participant |
| Engineer option B: individual EKS | 143 | 143 | $11,125 supplied estimate, about $77.80 per participant |
| Recommended: group environments on shared EKS | 50 to 60 | One shared instance per regional cohort | Requires a revised estimate and capacity test |

The supplied line items add up correctly. They are not validated quotations. They assume seven days of infrastructure runtime and omit enough inputs that the totals should remain planning estimates.

Reprice the agreed design rather than multiplying option A by 60/143. Shared services have fixed costs, regional platforms may be duplicated, and replacing dedicated RDS instances changes sizing.

| Assumption | Assessment and action |
|---|---|
| 143 RDS instances in option A | Valid for dedicated databases at the instance level, but different from our plan. Use separate databases/users on shared RDS. Restrict connection pools and measure total connections. |
| 16 workers, ten students per node | Plausible hypothesis, not measured capacity. At the supplied 725m CPU and 2.66 GiB per environment, ten environments request 7.25 vCPU and 26.6 GiB before platform overhead. Test startup, rollout and failure headroom. |
| Prefix delegation avoids 25 nodes | Prefix delegation can raise IP capacity. The exact node saving depends on pods per environment, daemon pods, subnet space and kubelet limits. It does not increase CPU or memory. [AWS guidance](https://docs.aws.amazon.com/eks/latest/userguide/cni-increase-ip-addresses.html). |
| Three ALBs for 143 environments | Depends on exposed services. With API, auth and analytics each using a target group, 143 environments need 429 target groups. At 100 target groups per ALB, at least five ALBs are needed. Three can accommodate two target groups per environment, with limited spare capacity. [AWS quotas](https://docs.aws.amazon.com/elasticloadbalancing/latest/application/load-balancer-limits.html). |
| One ALB per cohort in our earlier outline | Also conditional. Plan around 25 to 30 groups per ALB with three target groups each. Count all configured environments, including stopped workloads whose target groups remain. This corrects the earlier simplification. |
| Artifactory on m6i.large | Validate against concurrent clients and the installed version. JFrog's smallest published profile starts at four cores and 6 GB; the proposed two-vCPU instance is below that CPU baseline. Include its database, storage and licence. Prefer an existing licensed service. [JFrog sizing](https://docs.jfrog.com/installation/docs/hardware-sizing-matrix). |
| Artifactory plus 600 GB in ECR | Both can be intentional, but the artefact flow must explain why. Our baseline uses JFrog for application images. Remove the ECR application-storage allowance unless images will also be published there. |
| Parameter Store instead of Secrets Manager | Technically possible, but Secrets Manager is explicitly requested. Keep Secrets Manager. As an illustration, 180 secrets at $0.40 per month cost about $16.80 for seven days, before API/KMS charges. [AWS pricing](https://aws.amazon.com/secrets-manager/pricing/). |
| NAT, endpoints and transfer | State the region, AZ count and processed traffic. ECR interface endpoints have hourly and data charges. S3 gateway endpoints have no additional endpoint charge. Include cross-AZ traffic and public IPv4 charges where applicable. [PrivateLink pricing](https://aws.amazon.com/privatelink/pricing/), [VPC pricing](https://aws.amazon.com/vpc/pricing/). |
| Three-day CloudWatch retention | Controls storage, not ingestion. Price incoming GB, queries, metrics and alarms. Keep release evidence through assessment even if operational logs expire earlier. [CloudWatch pricing](https://aws.amazon.com/cloudwatch/pricing/). |
| Multi-account landing zone is mandatory | Multiple accounts are sensible for separate student estates. However, distinguish adjustable quotas from hard limits. EKS's published default of 100 clusters per account/region is adjustable. [EKS quotas](https://docs.aws.amazon.com/general/latest/gr/eks.html). |
| AWS Config is always required | Depends on the chosen governance baseline. Control Tower landing zone 4.0 supports optional service integrations. Fidelity policy can still require Config. [AWS documentation](https://docs.aws.amazon.com/controltower/latest/userguide/landing-zone-v4-migration-guide.html). |

Also include worker burst hours, Analytics volumes, Jenkins storage, backups, build-agent usage, software subscriptions and engineering/support time. Verify EC2/RDS rates for each selected region and purchasing model. No complete regional price quotation has been independently validated here.

**Answers to the application-sizing questions**

These observations come from the current reference working tree, including its uncommitted changes. Student implementations will vary.

| Question | Repository evidence and decision |
|---|---|
| JVM heap | Both Java Dockerfiles currently specify `MaxRAMPercentage=75`. Neither proves an appropriate Kubernetes memory limit. Measure total resident memory, including non-heap/native usage, before choosing heap and container limits. See [Trade REST API Dockerfile](../services/trade-api/Dockerfile) and [Trade Executor Dockerfile](../services/trade-executor/Dockerfile). |
| Angular dev server | Use a production build on S3/CloudFront. Angular consumes no EKS runtime pod memory in this plan. Its build still needs Jenkins agent memory. |
| Six extension modules | Six catalogue choices do not mean six additional services. Extensions remain inside the Trade REST API. India requires four integrated modules; US/Ireland selects one. Their caches and consumers still affect that process's memory. See [curriculum map](CURRICULUM_MAP.md). |
| Analytics CronJob or Deployment | The current [entrypoint](../analytics/docker-entrypoint.sh) serves HTTP, consumes Kafka and refreshes reports repeatedly. Keep it running as a Deployment with persistent storage. A CronJob would change behaviour and needs separate design work. The suggested 384 MiB is unverified. |
| Shared RDS connections | Current pool maxima are 10 for the Trade REST API, 5 for the Trade Executor and 10 for Auth. Sixty groups could permit 1,500 connections before Analytics and migration jobs. Reduce pools for training and size against measured concurrent demand. |
| Market-data traffic | Multiple pollers sharing one Fauxnance key can exhaust its quota. Use fixture mode for infrastructure tests. Allocate and verify live-feed access separately for assessments that require live data. |

The engineer is right that resource configuration can change costs materially. The supplied 725m/2.66 GiB aggregate and individual container budgets are assumptions, not measurements from this application.

**Keep instructor operations predictable**

Use fixed managed node groups sized for the scheduled classes. Defer Karpenter unless the platform engineer already operates and supports it. One NAT gateway per regional lab is a cost trade-off with a shared failure point.

Allow only engineering to manage shared ingress membership and routing. Block group-created `LoadBalancer` services, privileged containers and host access. Namespace quotas alone are insufficient isolation.

Start with three to five concurrent Jenkins builds. This limits build pressure, not the number of running group applications. Schedule a tested number of active groups, with a separate plan for showcase concurrency.

Stopping a group must retain its database and volumes. It does not stop charges for shared infrastructure or retained storage. Final cleanup removes the lab resources after assessment.

Before handover, engineering must provide:

1. A working reference release and tested CloudFormation/Helm/pipeline starters.
2. A capacity test covering the expected active groups, simultaneous builds, cold starts and rolling releases.
3. A restart and storage test for Kafka and DuckDB, plus a shared-RDS connection test.
4. A one-page instructor runbook with expected results and common failure fixes.
5. A remote platform support owner with coverage during both regions' teaching hours.
6. A regional cost estimate covering preparation, teaching, assessment and teardown, with an explicit contingency.

Obtain agreement on group environments with individual release assessment, regional group counts and simultaneous usage. Confirm JFrog availability and licensing before finalising the bill of materials.

Implementation starter: [CloudFormation templates and deployment runbook](../deploy/README.md). The kit separates trusted infrastructure provisioning from the student-editable application pipeline. It includes local validation; an AWS pilot remains required.
