from core.settings import get_settings, legacy_redis_config

_settings = get_settings()

OPENAI_API_KEY = _settings.openai_api_key
OPENAI_API_BASE = _settings.openai_api_base
JWT_SECRET_KEY = _settings.jwt_secret_key
JWT_ALGORITHM = _settings.jwt_algorithm
JWT_EXPIRATION_HOURS = _settings.jwt_expiration_hours
REDIS_CONFIG = legacy_redis_config()
