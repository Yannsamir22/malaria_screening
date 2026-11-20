from __future__ import annotations

import uuid
from dataclasses import dataclass
from typing import Annotated, Callable, Coroutine, Any

import jwt

from fastapi import Depends, Request, HTTPException
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

_bearer_schema = HTTPBearer(auto_error=False)

def _unauthorized() -> HTTPException:
      return HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
      )

@dataclass(frozen=True)
class Principal:
      id: uuid.UUID
      role: str
      
async def get_principal(
      request: Request,
      credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(_bearer_schema)]
) -> Principal:
      # Check that the credentials were provided
      if credentials is None or not credentials.credentials:
            raise _unauthorized()
      
      secret: str = request.app.state.settings.jwt_secret
      
      # 2. Decode and verify signature + required standard claims
      try:
            payload = jwt.decode(
                  credentials.credentials,
                  secret,
                  algorithms=["HS256"],
                  options={"require": ["exp", "iat", "sub"]}
            )
      except jwt.PyJWTError:
            raise _unauthorized()
      
      # 3. Verify token kind is "access"
      if payload.get("kind") != "access":
            raise _unauthorized()
      
      # 4. Parse `sub` claim as a valid UUID
      sub = payload.get("sub")
      if not isinstance(sub, str):
            raise _unauthorized()
      
      try:
            user_id = uuid.UUID(sub)
      except ValueError:
            raise _unauthorized()
      
      # 5. Verify `role` claim is present and non-empty
      role = payload.get("role")
      if not isinstance(role, str) or not role:
            raise _unauthorized()
      
      return Principal(id=user_id, role=role)
            
def require_roles(*roles: str):
      async def check(
            principal: Annotated[Principal, Depends(get_principal)],) -> Principal:
            if principal.role not in roles:
                  raise HTTPException(
                        status_code=403,
                        detail="Your role does not allow this operation"
                  )
            return principal
      return check
            