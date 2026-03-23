from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField
from wtforms.validators import DataRequired, Length


class QuickCaptureForm(FlaskForm):
    """Minimal single-field form — zero friction capture."""
    content = StringField(
        "What's on your mind?",
        validators=[DataRequired(), Length(1, 1000)]
    )
    submit = SubmitField('Capture')
