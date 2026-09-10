import base64
import json
import sys

import boto3
from botocore.auth import SigV4QueryAuth
from botocore.awsrequest import AWSRequest

cluster, region = sys.argv[1:]
session = boto3.Session(region_name=region)
request = AWSRequest(method="GET", url=f"https://sts.{region}.amazonaws.com/?Action=GetCallerIdentity&Version=2011-06-15",
                     headers={"x-k8s-aws-id": cluster})
SigV4QueryAuth(session.get_credentials().get_frozen_credentials(), "sts", region, expires=60).add_auth(request)
token = "k8s-aws-v1." + base64.urlsafe_b64encode(request.url.encode()).decode().rstrip("=")
print(json.dumps({"apiVersion": "client.authentication.k8s.io/v1beta1", "kind": "ExecCredential", "status": {"token": token}}))
