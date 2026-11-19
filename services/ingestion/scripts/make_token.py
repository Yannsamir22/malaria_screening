import argparse
from logging import root
import os
import sys
import uuid
from pathlib import Path

Path(__file__).resolve().parent.parent 
sys.path.insert(0, str(Path(__file__).parents[1] / "tests"))
from tokens import make_token

parser = argparse.ArgumentParser()
parser.add_argument("--role", required=True, choices=[
      "administrator", "clinician", "technician", "public_health_officer", "service"
])
parser.add_argument("--ttl", type=int, default=3600, help="lifetime in seconds")
parser.add_argument("--sub", default=None, help="the user id (a UUID); random when absent")
args = parser.parse_args()
if "JWT_SECRET" not in os.environ:
      sys.exit("Set JWT_SECRET first (the same value as the running service).")
      
print(make_token(args.role, uuid.UUID(args.sub) if args.sub else None,
                 ttl=args.ttl, secret=os.environ["JWT_SECRET"]))