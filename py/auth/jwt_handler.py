from auth.security import JWTHandler
from core.settings import get_settings

_settings = get_settings()
jwt_handler = JWTHandler(
    secret_key=_settings.jwt_secret_key,
    algorithm=_settings.jwt_algorithm,
    expiration_hours=_settings.jwt_expiration_hours,
)

__all__ = ["JWTHandler", "jwt_handler"]
