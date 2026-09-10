"""Generate learner links and scoped AWS policies after the shared stack is ready."""
import argparse
import csv
import json
from pathlib import Path
from urllib.parse import urlencode, urlsplit

import boto3
from package import policy


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--region", required=True)
    parser.add_argument("--shared-stack", required=True)
    parser.add_argument("--output", type=Path, default=Path("deploy/build/handover"))
    args = parser.parse_args()
    stack = boto3.client("cloudformation", region_name=args.region).describe_stacks(StackName=args.shared_stack)["Stacks"][0]
    if stack["StackStatus"] not in ("CREATE_COMPLETE", "UPDATE_COMPLETE"):
        raise ValueError("Shared stack is not ready")
    values = {o["OutputKey"]: o["OutputValue"] for o in stack["Outputs"]}
    account = stack["StackId"].split(":")[4]
    args.output.mkdir(parents=True, exist_ok=True)
    template = urlsplit(values["LearnerTemplateUrl"])
    template_arn = "arn:aws:s3:::" + template.netloc.split(".s3.")[0] + template.path
    with (args.output / "students.csv").open("w") as file:
        writer = csv.writer(file)
        writer.writerow(["Student", "Jenkins login", "Launch link", "CloudFormation role"])
        for number in range(1, int(values["StudentCount"]) + 1):
            student = f"s{number:03}"
            permissions = policy(account, args.region, values["PlatformName"], student,
                                 values["LearnerTemplateUrl"], values["LearnerExecutionRoleArn"])
            permissions["Statement"].append({"Effect": "Allow", "Action": "s3:GetObject", "Resource": template_arn})
            (args.output / (student + ".json")).write_text(json.dumps(permissions, indent=2) + "\n")
            query = urlencode({"templateURL": values["LearnerTemplateUrl"], "stackName": student,
                               "param_PlatformName": values["PlatformName"]})
            url = f"https://{args.region}.console.aws.amazon.com/cloudformation/home?region={args.region}#/stacks/create/review?{query}"
            writer.writerow([student, values["PlatformName"] + "-" + student, url, values["LearnerExecutionRoleArn"]])
    print("Handover files written to " + str(args.output))


if __name__ == "__main__":
    main()
