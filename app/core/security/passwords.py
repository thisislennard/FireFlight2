from werkzeug.security import check_password_hash, generate_password_hash


def hash_password(plain: str) -> str:
    return generate_password_hash(plain)


def verify_password(password_hash: str, plain: str) -> bool:
    return check_password_hash(password_hash, plain)
