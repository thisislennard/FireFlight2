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

    # Globaler Not-Aus-Schalter (Default an) — Zugangsdaten/DSGVO-Bestätigung pro Organisation kommen
    # aus der Administrationsoberfläche (IntegrationConfig), s. app/integrations/dji_flighthub/service.py.
    DJI_FLIGHTHUB_ENABLED = os.environ.get("DJI_FLIGHTHUB_ENABLED", "true").lower() == "true"
    DJI_FLIGHTHUB_BASE_URL = os.environ.get("DJI_FLIGHTHUB_BASE_URL", "https://fh.dji.com")
    DJI_FLIGHTHUB_ORG_KEY = os.environ.get("DJI_FLIGHTHUB_ORG_KEY", "")
    DJI_FLIGHTHUB_PROJECT_UUID = os.environ.get("DJI_FLIGHTHUB_PROJECT_UUID", "")

    LOGIN_MAX_FAILED_ATTEMPTS = 5
    LOGIN_LOCKOUT_MINUTES = 15


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
