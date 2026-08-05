import os

from app.exceptions import MissingConfigurationError


def require_setting(name: str) -> str:
    value = os.getenv(name)
    if not value:
        raise MissingConfigurationError(f"Required setting {name} is missing")
    return value

