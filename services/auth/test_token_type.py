import jwt
from uuid import uuid4

from app.config import Settings
from app.security import create_token, decode_token

settings = Settings(
    jwt_secret="0123456789abcdef0123456789abcdef"
)

token = create_token(
    settings,
    str(uuid4()),
    "administrator",
    "refresh"
)

try:
    decode_token(settings, token, "access")
    print("ERROR: Refresh token was accepted")
except jwt.InvalidTokenError:
    print("SUCCESS: Refresh token rejected as access token")
