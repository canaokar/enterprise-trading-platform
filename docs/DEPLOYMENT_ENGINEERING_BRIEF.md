# Deployment brief for engineering

Provide 143 individual environments on shared AWS infrastructure. Students can deploy from their group repository.

**Part 1: engineering.** Launch the shared CFT for VPC, EKS, shared RDS, ALBs, certificates and logging. Complete the EKS setup and prepare the Jenkins jobs, agents, JFrog credentials and individual AWS access before class.

**Part 2: graduates.** Launch the learner CFT with the assigned values, then run the assigned Jenkins job. The CFT creates their frontend resources, secrets, routes, logs and release role. Jenkins prepares their namespace and database, then builds and deploys their containers and frontend. Later GitHub pushes trigger new releases.

Instructors guide these steps and help diagnose code failures. Engineering owns platform failures and final cleanup. Students and instructors do not run bootstrap scripts or Kubernetes setup commands.

Use the [deployment guide and templates](../deploy/README.md). Test two students end to end before classroom handover.
