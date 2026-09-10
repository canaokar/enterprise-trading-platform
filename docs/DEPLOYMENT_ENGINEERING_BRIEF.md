**Deployment brief for engineering**

We need a two-part CloudFormation deployment process for the Fidelity graduate programme. Engineering prepares the platform. Each graduate launches their own application environment. Instructors guide the exercise using a short runbook.

Plan for 143 individual environments across the regional cohorts. Students can deploy the code from their group's repository. This replaces the earlier assumption of 50 to 60 group environments with sequential individual releases.

**Part 1: engineering launches the shared CFT**

Engineering supplies the account, region, domain, access and registry configuration, then launches the shared template once per regional cohort.

The stack creates the shared VPC, EKS cluster and worker capacity, RDS PostgreSQL instance, HTTPS load balancers, certificates and monitoring. It also sets up or connects the shared Jenkins and JFrog services and installs all required platform automation.

Engineering then gives instructors the learner template launch link, access instructions and a tested reference deployment. Each student receives their own AWS login with permissions limited to the exercise.

Expected result: the platform is ready for learner stacks. All platform bootstrap work runs as part of the engineering-owned automation.

**Part 2: each graduate launches the learner CFT**

The graduate signs in, opens the supplied launch link and enters their GitHub repository and branch. The assigned stack name supplies their student ID. Shared-platform settings are prefilled.

The learner stack provisions:

| Student-owned component | Where it runs |
|---|---|
| Trade REST API, Trade Executor, Auth and Analytics | Their namespace in the shared EKS cluster |
| Kafka and persistent application storage | Their own broker and volumes in that namespace |
| Database and credentials | Their own database/user on shared RDS, with secrets stored in Secrets Manager |
| Angular frontend | Their own private S3 bucket and CloudFront distribution |
| Application access and logs | Their own HTTPS routes and CloudWatch log group |
| Delivery pipeline | Their own job on shared Jenkins, connected to their GitHub repository |

Creating the learner stack triggers Jenkins to build, publish to JFrog and deploy the initial application. The stack outputs the application URL and Jenkins job URL. Students wait for the first successful Jenkins build before opening the application.

Subsequent releases follow: GitHub push or merge to the configured branch, Jenkins build and tests, image publication, application deployment. Students can share source code while deploying to separate environments.

**Responsibilities and acceptance**

| Stakeholder | Responsibility |
|---|---|
| Engineering | Build and test both templates and their automation, size the platform, provide accounts/access, and support infrastructure failures remotely |
| Instructors | Guide students through the learner CFT, help interpret build/application failures, and assess the deployed application |
| Graduates | Launch their learner CFT, release their code through Jenkins, demonstrate the application and clean up their environment |

The acceptance test is that an instructor can follow the supplied instructions with a fresh student login and obtain a working application through the learner CFT. No separate Python, Helm, kubectl or database bootstrap commands should be required from students or instructors. Deleting a learner stack must clean up that student's resources under the documented retention policy without affecting anyone else.

Engineering owns the implementation behind these two entry points. With EKS, some Kubernetes, database and Jenkins operations need custom provisioning automation invoked by CloudFormation. Include creation, failure handling, updates and deletion in that automation. [AWS custom resource documentation](https://docs.aws.amazon.com/AWSCloudFormation/latest/UserGuide/template-custom-resources.html).

The [replacement kit](../deploy/README.md) implements these two entry points. It connects existing Jenkins and JFrog services and uses a setup function for Kubernetes, database and job provisioning. Complete the AWS pilot before classroom use.
