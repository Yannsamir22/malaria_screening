import time
from dataclasses import dataclass
from uuid import UUID

import jwt
from argon2 import PasswordHasher
from argon2.exceptions import VerificationError, InvalidHashError

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.config import Settings

bearer_scheme = HTTPBearer(auto_error=False)
password_hasher = PasswordHasher()

def hash_password(password: str) -> str:
    return password_hasher.hash(password)

def verify_password(password: str, password_hash: str) -> bool:
    try:
        return password_hasher.verify(password_hash, password)
    except (VerificationError, InvalidHashError):
        return False

@dataclass(frozen=True)
class Principal:
    id: UUID
    role: str

def create_token(settings: Settings, sub: str, role: str, kind: str) -> str:
    now = int(time.time())

    if kind == "access":
        ttl = settings.access_ttl
    elif kind == "refresh":
        ttl = settings.refresh_ttl
    else:
        raise ValueError("Invalid token type.")

    payload = {
        "sub": str(sub),
        "role": str(role),
        "type": kind,
        "iat": now,
        "exp": now + ttl,
    }

    return jwt.encode(
        payload,
        settings.jwt_secret,
        algorithm="HS256"
    )

def decode_token(settings: Settings, token: str, kind: str) -> dict:
    payload = jwt.decode(
        token,
        settings.jwt_secret,
        algorithms=["HS256"],
        options={"require": ["exp", "iat", "sub"]}
    )

    if payload.get("type") != kind:
        raise jwt.InvalidTokenError("Invalid token type.")

    return payload

def get_principal(
    request: Request,
    credentials: HTTPAuthorizationCredentials | None = Depends(bearer_scheme)
) -> Principal:

    if credentials is None:
        raise HTTPException(
            status_code=401,
            detail="Not authenticated",
            headers={"WWW-Authenticate": "Bearer"}
        )

    settings = request.app.state.settings

    try:
        payload = decode_token(
            settings,
            credentials.credentials,
            "access"
        )

        user_id = UUID(payload["sub"])
        role = payload["role"]

        if not isinstance(role, str):
            raise ValueError("Invalid role")

        return Principal(id=user_id, role=role)

    except (jwt.PyJWTError, ValueError, KeyError, TypeError):
        raise HTTPException(
            status_code=401,
            detail="Invalid or expired token",
            headers={"WWW-Authenticate": "Bearer"}
        )

def require_roles(*roles: str):
    def dependency(
        principal: Principal = Depends(get_principal)
    ) -> Principal:

        if principal.role not in roles:
            raise HTTPException(
                status_code=403,
                detail="Insufficient permissions"
            )

        return principal

    return dependency 