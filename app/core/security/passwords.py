from werkzeug.security import check_password_hash, generate_password_hash

# Leicht erratbare PINs, die trotz gültigen 4-Ziffern-Formats nicht zugelassen werden (Selbstwahl per
# PinChangeForm, Admin-Anlageformular) -- bei nur 10.000 möglichen Kombinationen ist das eine billige,
# wirksame Maßnahme gegen die häufigsten real beobachteten PIN-Verteilungen.
TRIVIAL_PINS = {
    "0000", "1111", "2222", "3333", "4444", "5555", "6666", "7777", "8888", "9999",
    "1234", "4321", "0123", "2580", "1212", "1004", "6969",
}


def hash_pin(plain: str) -> str:
    return generate_password_hash(plain)


def verify_pin(pin_hash: str, plain: str) -> bool:
    return check_password_hash(pin_hash, plain)


def is_trivial_pin(pin: str) -> bool:
    return pin in TRIVIAL_PINS
