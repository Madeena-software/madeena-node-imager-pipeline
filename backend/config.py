"""Flask application configuration."""

import os
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = os.path.dirname(os.path.abspath(__file__))


def _get_env_int(name: str, default: int) -> int:
    """Read integer env var with fallback."""
    try:
        return int(os.environ.get(name, default))
    except (TypeError, ValueError):
        return default


def _get_env_bool(name: str, default: bool) -> bool:
    """Read boolean env var with fallback."""
    raw_value = os.environ.get(name)
    if raw_value is None:
        return default
    return raw_value.strip().lower() in {"1", "true", "yes", "on"}


class Config:
    """Base configuration."""

    SECRET_KEY = os.environ.get("SECRET_KEY", os.urandom(24).hex())
    MAX_CONTENT_LENGTH = int(os.environ.get("MAX_CONTENT_LENGTH", 512 * 1024 * 1024))

    # Default crop values (pixels removed from each side)
    CROP_TOP = max(0, _get_env_int("CROP_TOP", 0))
    CROP_BOTTOM = max(0, _get_env_int("CROP_BOTTOM", 0))
    CROP_LEFT = max(0, _get_env_int("CROP_LEFT", 0))
    CROP_RIGHT = max(0, _get_env_int("CROP_RIGHT", 0))

    CORS_ORIGINS = os.environ.get("CORS_ORIGINS", "*")

    HOST = os.environ.get("HOST", "0.0.0.0")
    PORT = int(os.environ.get("PORT", 5000))

    ALLOWED_EXTENSIONS = frozenset(
        {"png", "jpg", "jpeg", "gif", "bmp", "tiff", "tif", "webp", "ico", "jfif"}
    )


class DevelopmentConfig(Config):
    """Development configuration."""

    DEBUG = True


class ProductionConfig(Config):
    """Production configuration."""

    DEBUG = False


class TestingConfig(Config):
    """Testing configuration."""

    TESTING = True
    UPLOAD_FOLDER = os.path.join(BASE_DIR, "test_uploads")
    OUTPUT_FOLDER = os.path.join(BASE_DIR, "test_outputs")


config_by_name = {
    "development": DevelopmentConfig,
    "production": ProductionConfig,
    "testing": TestingConfig,
}


def get_config():
    """Return the config object based on FLASK_ENV."""
    env = os.environ.get("FLASK_ENV", "development")
    return config_by_name.get(env, DevelopmentConfig)
