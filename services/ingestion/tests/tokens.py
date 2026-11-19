import time 
import uuid

import jwt
SECRET = "test-secret-for-the-ingestion-service-0123456789" # Only for test

def make_token(role, user_id=None, kind="access", ttl=900, secret=SECRET) -> str:
      now = int(time.time())
      payload = {
            "sub": str(user_id or uuid.uuid4()),
            "role": role,
            "kind": kind,
            "iat": now,
            "exp": now + ttl
      }
      return jwt.encode(payload, secret, algorithm="HS256")