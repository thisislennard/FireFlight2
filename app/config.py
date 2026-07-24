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

    # Web-Push (app/notifications/): Rohes base64url-kodiertes Schlüsselpaar, erzeugt per
    # `flask notifications generate-vapid-keys` -- kein Parallelbetrieb mehrerer Formate, pywebpush
    # akzeptiert dieses Format direkt (py_vapid.Vapid.from_string).
    VAPID_PUBLIC_KEY = os.environ.get("VAPID_PUBLIC_KEY", "")
    VAPID_PRIVATE_KEY = os.environ.get("VAPID_PRIVATE_KEY", "")
    VAPID_CLAIMS_EMAIL = os.environ.get("VAPID_CLAIMS_EMAIL", "admin@example.org")

    # Externe Dashboard-Widgets (Phase 14, Konzeptdokument: "Wetterdaten vom DWD" / "OpenSkyMap").
    # Bewusst "schlanke Direktanbindung" statt eigener Integrationsschicht mit Admin-Konfiguration
    # (Nutzerentscheidung nach der DJI-FlightHub-Erfahrung, s. docs/roadmap.md Phase 14) -- daher
    # hier als Konstanten statt über eine Admin-UI. Standort: Feuerwehr Liederbach am Taunus,
    # identisch mit dem seit Phase 9 verwendeten Karten-Fallback-Mittelpunkt
    # (app/static/js/incidents_widget_map.js).
    WEATHER_LOCATION_LAT = 50.08
    WEATHER_LOCATION_LON = 8.45
    WEATHER_CACHE_SECONDS = 600  # 10 Min. -- DWD-Messwerte aktualisieren sich ohnehin nur stündlich.

    OPENSKY_LOCATION_LAT = 50.08
    OPENSKY_LOCATION_LON = 8.45
    OPENSKY_RADIUS_KM = 50
    # OpenSky erlaubt anonymen Clients nur 400 Requests/Tag -- 300s TTL begrenzt den Verbrauch auf
    # max. 288 Requests/Tag selbst bei durchgehender Nutzung, mit Puffer nach unten.
    OPENSKY_CACHE_SECONDS = 300


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

    # Wegwerf-Schlüsselpaar, nur damit send_to_user() in Tests nicht an der VAPID-Konfigurationsprüfung
    # scheitert -- der tatsächliche Push-Versand wird in Tests gemockt (pywebpush.webpush), diese
    # Schlüssel gehen nie über das Netz.
    VAPID_PUBLIC_KEY = "BHh0biAhgoi46fceDwZfnuyTYmlT9wBySbiBmIA50aWDY35cMjftQ0Yr9rPie2aW9D6RP3Wt6kdK0lwRy5IqbGU"
    VAPID_PRIVATE_KEY = "p1YZZZiqlcChriFCf37PDascoVVVYIHg_Wg3O1jYyio"


class ProductionConfig(BaseConfig):
    DEBUG = False


CONFIG_BY_NAME = {
    "development": DevelopmentConfig,
    "testing": TestingConfig,
    "production": ProductionConfig,
}


def get_config_name() -> str:
    return os.environ.get("FLASK_ENV", "production")
