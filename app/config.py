import os


class BaseConfig:
    SECRET_KEY = os.environ.get("SECRET_KEY", "dev-insecure-secret-key-change-me")
    SQLALCHEMY_DATABASE_URI = os.environ.get("DATABASE_URL", "")
    SQLALCHEMY_ENGINE_OPTIONS = {"pool_pre_ping": True}
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    TIMEZONE = os.environ.get("TIMEZONE", "Europe/Berlin")

    SESSION_COOKIE_HTTPONLY = True
    SESSION_COOKIE_SAMESITE = "Lax"
    SESSION_COOKIE_SECURE = os.environ.get("SESSION_COOKIE_SECURE", "true").lower() == "true"
    SESSION_PROTECTION = "strong"

    WTF_CSRF_TIME_LIMIT = None

    MAX_CONTENT_LENGTH = 16 * 1024 * 1024

    # Bei nur 10.000 möglichen 4-stelligen PINs bietet der Hash praktisch keinen Brute-Force-Schutz
    # mehr -- Lockout ist die einzige wirksame Verteidigung, daher niedrigerer Schwellwert als bei
    # Passwörtern üblich und progressive Sperrstufen (app/auth/services.py:_register_failed_attempt).
    LOGIN_MAX_FAILED_ATTEMPTS = 3
    LOGIN_LOCKOUT_STAGES_MINUTES = [15, 60]  # 1./2. Sperre; ab der 3. Sperre: requires_admin_unlock


class DevelopmentConfig(BaseConfig):
    DEBUG = True
    SESSION_COOKIE_SECURE = False


class TestingConfig(BaseConfig):
    TESTING = True
    DEBUG = True
    SESSION_COOKIE_SECURE = False
    WTF_CSRF_ENABLED = False
    RATELIMIT_ENABLED = False
    SQLALCHEMY_DATABASE_URI = os.environ.get("TEST_DATABASE_URL", BaseConfig.SQLALCHEMY_DATABASE_URI)


class ProductionConfig(BaseConfig):
    DEBUG = False


CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config_name() -> str:
    return os.environ.get("FLASK_ENV", "production")
