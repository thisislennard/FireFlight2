from flask_wtf import FlaskForm
from wtforms import PasswordField, StringField
from wtforms.validators import DataRequired, Length


class LoginForm(FlaskForm):
    identifier = StringField("Benutzername oder E-Mail", validators=[DataRequired(), Length(max=255)])
    password = PasswordField("Passwort", validators=[DataRequired()])
