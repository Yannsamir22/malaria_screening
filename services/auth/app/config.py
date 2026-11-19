import os
from dataclasses import dataclass

@dataclass(frozen=True)
class Settings:
    jwt_secret: str
    access_ttl: int = 900
    refresh_ttl: int = 604800
    bootstrap_admin_email: str | None = None
    bootstrap_admin_password: str | None = None

    def __post_init__(self) -> None:
        if len(self.jwt_secret.encode("utf-8")) < 32:
            raise RuntimeError("JWT_SECRET must be at least 32 bytes long.")

    @classmethod
    def from_env(cls) -> "Settings":
        jwt_secret = os.getenv("JWT_SECRET")

        if not jwt_secret:
            raise RuntimeError("JWT_SECRET environment variable is required.")

        return cls(
            jwt_secret=jwt_secret,
            bootstrap_admin_email=os.getenv("BOOTSTRAP_ADMIN_EMAIL"),
            bootstrap_admin_password=os.getenv("BOOTSTRAP_ADMIN_PASSWORD"),
        )