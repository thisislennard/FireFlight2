class FireFlightError(Exception):
    """Basisklasse für fachliche Fehler, die auf eine HTTP-Antwort abgebildet werden."""


class PermissionDenied(FireFlightError):
    def __init__(self, permission_key: str):
        self.permission_key = permission_key
        super().__init__(f"Fehlende Berechtigung: {permission_key}")


class ValidationError(FireFlightError):
    def __init__(self, message: str):
        self.message = message
        super().__init__(message)


class NotFoundError(FireFlightError):
    def __init__(self, message: str = "Nicht gefunden"):
        self.message = message
        super().__init__(message)
