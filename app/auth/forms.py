from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, EqualTo, Length, Regexp
from wtforms.validators import ValidationError as WTFormsValidationError

PIN_REGEXP = Regexp(r"^\d{4}$", message="Die PIN muss aus genau 4 Ziffern bestehen.")


class LoginForm(FlaskForm):
    identifier = StringField("Benutzername oder E-Mail", validators=[DataRequired(), Length(max=255)])
    pin = PasswordField("PIN", validators=[DataRequired(), PIN_REGEXP])


class PinChangeForm(FlaskForm):
    current_pin = PasswordField("Aktuelle PIN", validators=[DataRequired(), PIN_REGEXP])
    new_pin = PasswordField("Neue PIN", validators=[DataRequired(), PIN_REGEXP])
    new_pin_confirm = PasswordField(
        "Neue PIN bestätigen",
        validators=[DataRequired(), EqualTo("new_pin", message="Die PINs stimmen nicht überein.")],
    )

    def validate_new_pin(self, field):
        from app.core.security.passwords import is_trivial_pin

        if is_trivial_pin(field.data):
            raise WTFormsValidationError("Diese PIN ist zu leicht zu erraten. Bitte eine andere PIN wählen.")
