# Deployment approach

Use one shared AWS platform per regional cohort and one application environment per graduate. Plan for 143 environments, with separate databases and Kubernetes namespaces.

Engineering launches the shared CloudFormation template and prepares EKS, Jenkins, JFrog and access. Graduates launch their CloudFormation template and run their assigned Jenkins job. Jenkins builds from GitHub, publishes images to JFrog and deploys the application.

CloudFormation owns AWS resources. Engineering maintains the Kubernetes and database preparation run by Jenkins. Instructors guide students through stack creation, builds and the application demonstration.

The [deployment guide](../deploy/README.md) defines the two parts, resource ownership, setup and cleanup. The [engineering brief](DEPLOYMENT_ENGINEERING_BRIEF.md) is the short handover.
