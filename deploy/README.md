# Graduate deployment kit

Two CloudFormation templates. Engineering runs [shared.yaml](shared.yaml) once per regional cohort. Each graduate runs [learner.yaml](learner.yaml) once for their own environment.

The kit is for 143 individual deployments. Students can use their group's GitHub repository while keeping separate applications and data.

## Part 1: engineering prepares the platform

Engineering packages the kit, connects the existing Jenkins and JFrog services, and launches the shared stack. The [engineering guide](engineering.md) contains the commands and prerequisites.

The stack creates the VPC, EKS cluster and workers, shared RDS PostgreSQL, HTTPS load balancers, certificate, logging and setup function. Kubernetes platform setup runs automatically.

Engineering tests two learner deployments, then provides individual AWS logins, learner launch links, the CloudFormation role and Jenkins access. Account provisioning stays with engineering.

## Part 2: graduates deploy their application

1. Sign in to AWS and open your assigned launch link. Keep the supplied stack name, such as `s001`, and platform name.
2. Enter your GitHub repository and branch. Under **Permissions**, select the CloudFormation role supplied by your instructor. Acknowledge IAM resource creation and choose **Create stack**.
3. Wait for `CREATE_COMPLETE`. Open **Outputs**, then `JenkinsUrl`. Wait for the first successful build before opening `ApplicationUrl`.
4. Push further changes to the same branch. Jenkins checks for changes every two minutes, then tests, publishes and deploys them.

| Each graduate gets | Location |
|---|---|
| Trade REST API, Trade Executor, Auth and Analytics | Their namespace on shared EKS |
| Kafka and persistent storage | Their broker and two volumes in that namespace |
| Database and credentials | Their database/user on shared RDS and their Secrets Manager secrets |
| Angular frontend | Their private S3 bucket and CloudFront distribution |
| HTTPS routes and logs | Shared load balancer, separate routes and CloudWatch log groups |
| Delivery pipeline | Their Jenkins job and isolated build worker |

`CREATE_COMPLETE` means the environment is provisioned and Jenkins has been triggered. The application is ready when the Jenkins build succeeds. Students and instructors do not run setup scripts, Helm or kubectl.

## Instructor runbook

Start with three students at a time. Increase the wave size only after engineering confirms capacity.

| Situation | Action |
|---|---|
| Stack is still creating | Read its Events tab. Wait for resource creation to finish. |
| Stack fails | Send the stack name and failed event to engineering. Keep the assigned ID. |
| Jenkins tests or build fail | Help the student fix the reported error and push again. |
| Several students fail together | Escalate to engineering before starting more deployments. |
| Assessment | Demonstrate login, an executed order, persisted data and application logs. |
| Lab is finished | After assessment, delete the student's CloudFormation stack. |

Deleting a learner stack removes its application, database, volumes, frontend, registry images and Jenkins job. This deletes its lab data. Engineering deletes the shared stack after all learner stacks are gone.

Engineering owns infrastructure reliability and classroom capacity. Instructors guide and assess. Graduates launch, release and demonstrate their application.

This kit requires an AWS pilot before classroom use. Local validation does not establish live IAM permissions, integration compatibility or cohort capacity.
