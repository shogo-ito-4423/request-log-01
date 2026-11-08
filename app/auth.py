"""Small, provisioned-user bearer authentication (no self-service accounts)."""

import hashlib
import hmac
import os
from typing import Annotated, Literal

from fastapi import Depends, HTTPException, Request
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from pydantic import BaseModel, ConfigDict, Field, TypeAdapter, ValidationError


class Principal(BaseModel):
    model_config = ConfigDict(extra="forbid", frozen=True)

    user_id: str = Field(pattern=r"^[a-zA-Z0-9_-]{1,100}$")
    role: Literal["user", "admin"]
    token_sha256: str = Field(pattern=r"^[0-9a-f]{64}$")


def load_users() -> list[Principal]:
    try:
        users = TypeAdapter(list[Principal]).validate_json(os.getenv("AUTH_USERS_JSON", ""))
        if not users or len({u.user_id for u in users}) != len(users):
            raise ValueError
        if len({u.token_sha256 for u in users}) != len(users):
            raise ValueError
        return users
    except (ValueError, ValidationError):
        raise ValueError("AUTH_USERS_JSON must contain unique users and token hashes") from None


bearer = HTTPBearer(auto_error=False)


def current_user(
    request: Request,
    credentials: Annotated[HTTPAuthorizationCredentials | None, Depends(bearer)],
) -> Principal:
    if credentials is not None:
        digest = hashlib.sha256(credentials.credentials.encode()).hexdigest()
        for user in request.app.state.auth_users:
            if hmac.compare_digest(digest, user.token_sha256):
                return user
    raise HTTPException(
        status_code=401, detail="Authentication required", headers={"WWW-Authenticate": "Bearer"}
    )


UserDep = Annotated[Principal, Depends(current_user)]


def require_owner(user: Principal, owner_id: str | None) -> None:
    if user.role != "admin" and user.user_id != owner_id:
        raise HTTPException(status_code=403, detail="Operation not permitted")
