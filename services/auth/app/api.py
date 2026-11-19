from typing import Annotated
import jwt
from uuid import UUID
from app.schemas import RefreshRequest
from app.security import decode_token

from fastapi import APIRouter, Depends, HTTPException, Request

from app.config import Settings
from app.store import UserStore
from app.security import Principal, get_principal, require_roles

from fastapi import status

from app.schemas import RegisterRequest, User
from app.security import hash_password

from app.schemas import LoginRequest, TokenPair
from app.security import verify_password, create_token
from fastapi import Query
from app.schemas import Role, UserStatus, UserList
from app.schemas import UserPatch

router = APIRouter(prefix="/api/v1")

def get_store(request: Request) -> UserStore:
    return request.app.state.store


def get_settings(request: Request) -> Settings:
    return request.app.state.settings

Store = Annotated[UserStore, Depends(get_store)]

Cfg = Annotated[Settings, Depends(get_settings)]

Me = Annotated[Principal, Depends(get_principal)]

Admin = Annotated[
    Principal,
    Depends(require_roles("administrator"))
]

def find(store: UserStore, user_id: str) -> dict:
    user = store.get(user_id)

    if user is None:
        raise HTTPException(
            status_code=404,
            detail="User not found"
        )

    return user

from app.schemas import Health


@router.get(
    "/health",
    response_model=Health,
    operation_id="getHealth"
)
def get_health():
    return {
        "status": "ok",
        "service": "auth-service"
    }

@router.post(
    "/auth/register",
    response_model=User,
    status_code=status.HTTP_201_CREATED,
    response_model_exclude_none=True,
    operation_id="registerUser"
)
def register_user(
    body: RegisterRequest,
    store: Store,
    admin: Admin
):
    email = str(body.email).lower()

    if store.get_by_email(email) is not None:
        raise HTTPException(
            status_code=409,
            detail="Email already registered"
        )

    fields = body.model_dump(mode="json")
    fields["email"] = email

    password = fields.pop("password")
    fields["password_hash"] = hash_password(password)

    return store.add(fields)

@router.post(
    "/auth/login",
    response_model=TokenPair,
    operation_id="loginUser"
)
def login_user(
    body: LoginRequest,
    store: Store,
    settings: Cfg
):
    email = str(body.email).lower()

    user = store.get_by_email(email)

    if user is None or not verify_password(
        body.password,
        user["password_hash"]
    ):
        raise HTTPException(
            status_code=401,
            detail="Invalid email or password"
        )

    if user["status"] != "active":
        raise HTTPException(
            status_code=403,
            detail="Account is deactivated"
        )

    return issue_tokens(settings, user)

def issue_tokens(settings: Settings, user: dict) -> dict:
    return {
        "access_token": create_token(
            settings,
            user["id"],
            user["role"],
            "access"
        ),
        "refresh_token": create_token(
            settings,
            user["id"],
            user["role"],
            "refresh"
        ),
        "token_type": "bearer",
        "expires_in": settings.access_ttl
    }

@router.post(
    "/auth/refresh",
    response_model=TokenPair,
    operation_id="refreshToken"
)
def refresh_token(
    body: RefreshRequest,
    store: Store,
    settings: Cfg
):
    try:
        payload = decode_token(
            settings,
            body.refresh_token,
            "refresh"
        )
        user_id = str(UUID(payload["sub"]))
    except (jwt.PyJWTError, ValueError, KeyError, TypeError):
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token"
        )

    user = store.get(user_id)

    if user is None or user["status"] != "active":
        raise HTTPException(
            status_code=401,
            detail="Invalid refresh token"
        )

    return issue_tokens(settings, user)

@router.get(
    "/users/me",
    response_model=User,
    response_model_exclude_none=True,
    operation_id="getCurrentUser"
)
def get_current_user(
    store: Store,
    me: Me
):
    user = store.get(str(me.id))

    if user is None or user["status"] != "active":
        raise HTTPException(
            status_code=401,
            detail="Invalid or inactive user"
        )

    return user

@router.get(
    "/users",
    response_model=UserList,
    operation_id="listUsers"
)
def list_users(
    store: Store,
    admin: Admin,
    role: Role | None = None,
    status: UserStatus | None = None,
    limit: Annotated[int, Query(ge=1, le=100)] = 10,
    offset: Annotated[int, Query(ge=0)] = 0
):
    users = store.list(
        role=role,
        status=status,
        limit=limit,
        offset=offset
    )

    return {"users": users}

@router.get(
    "/users/{user_id}",
    response_model=User,
    response_model_exclude_none=True,
    operation_id="getUser"
)
def get_user(
    user_id: UUID,
    store: Store,
    me: Me
):
    if me.role != "administrator" and me.id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Your role does not allow this operation"
        )

    return find(store, str(user_id))

@router.patch(
    "/users/{user_id}",
    response_model=User,
    response_model_exclude_none=True,
    operation_id="updateUser"
)
def update_user(
    user_id: UUID,
    body: UserPatch,
    store: Store,
    me: Me
):
    is_admin = me.role == "administrator"

    if not is_admin and me.id != user_id:
        raise HTTPException(
            status_code=403,
            detail="Your role does not allow this operation"
        )

    changes = body.model_dump(
        mode="json",
        exclude_unset=True
    )

    if "role" in changes and not is_admin:
        raise HTTPException(
            status_code=403,
            detail="Your role does not allow this operation"
        )

    find(store, str(user_id))

    return store.update(str(user_id), changes)

USER_MOVES = {
    "deactivate": {
        "active": "deactivated"
    },
    "reactivate": {
        "deactivated": "active"
    }
}

def move(store: UserStore, user_id: str, action: str):
    user = find(store, user_id)

    current_status = user["status"]

    next_status = USER_MOVES[action].get(current_status)

    if next_status is None:
        raise HTTPException(
            status_code=409,
            detail=f"Cannot {action} a user who is {current_status}"
        )

    return store.set_status(user_id, next_status)

@router.post(
    "/users/{user_id}/deactivate",
    response_model=User,
    response_model_exclude_none=True,
    operation_id="deactivateUser"
)
def deactivate_user(
    user_id: UUID,
    store: Store,
    admin: Admin
):
    return move(store, str(user_id), "deactivate")

@router.post(
    "/users/{user_id}/reactivate",
    response_model=User,
    response_model_exclude_none=True,
    operation_id="reactivateUser"
)
def reactivate_user(
    user_id: UUID,
    store: Store,
    admin: Admin
):
    return move(store, str(user_id), "reactivate")