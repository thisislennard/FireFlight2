from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired

from app.auth.forms import PIN_REGEXP


class DevicePairForm(FlaskForm):
    device_key = StringField("Geräteschlüssel", validators=[DataRequired()])


class RcPinForm(FlaskForm):
    """Schritt 2 des RC-Logins (Konzeptdokument Abschnitt 5.1) -- nur PIN, kein Identifier-Feld: der
    Nutzer wurde in Schritt 1 bereits per Antippen aus der qualifikationsgefilterten Liste
    ausgewählt, nicht eingetippt."""

    pin = PasswordField("PIN", validators=[DataRequired(), PIN_REGEXP])
