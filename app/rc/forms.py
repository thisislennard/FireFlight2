from flask_wtf import FlaskForm
from wtforms import StringField
from wtforms.validators import DataRequired


class DevicePairForm(FlaskForm):
    device_key = StringField("Geräteschlüssel", validators=[DataRequired()])
