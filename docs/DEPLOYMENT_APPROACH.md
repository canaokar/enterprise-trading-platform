# Deployment approach

Use one shared AWS platform per regional cohort and one application environment per graduate.

Engineering launches the shared CFT, which creates VPC, EKS, RDS, ALBs, certificates and logging, installs the cluster components and creates the Jenkins jobs. Existing Jenkins/JFrog services and account access are engineering prerequisites.

Graduates launch their learner CFT and run the linked Jenkins job. Each gets their own containers, Kafka, database, secrets and frontend. Jenkins uses a common pool of disposable build agents with temporary permissions for the current student.

Follow the [deployment guide](../deploy/README.md). Instructors guide deployment and diagnose code failures; engineering supports shared infrastructure.
