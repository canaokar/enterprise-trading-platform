# Deployment brief for engineering

Provide 143 individual deployments on shared EKS and RDS.

1. **Engineering:** prepare the existing Jenkins/JFrog services and AWS access, then launch the shared CFT. It creates AWS infrastructure, installs the EKS components and creates the student Jenkins jobs. Use one common pool of disposable build agents.
2. **Graduates:** launch the learner CFT with their assigned values and GitHub repository, then select Build Now in the job linked from the stack. Jenkins prepares and deploys their application. Later GitHub changes trigger builds.

Instructors guide these steps and help with code failures. Engineering owns infrastructure support and cleanup.

The [deployment guide](../deploy/README.md) contains the setup and classroom instructions. Run two student deployments before handover. The AWS/Jenkins pilot has not yet been run.
