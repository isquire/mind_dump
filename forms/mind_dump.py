from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, HiddenField
from wtforms.validators import DataRequired, Length


class QuickCaptureForm(FlaskForm):
    """Minimal single-field form — zero friction capture."""
    content = StringField(
        "What's on your mind?",
        validators=[DataRequired(), Length(1, 1000)]
    )
    # Set by the inline Work/Personal toggle button; falls back to time-based default in route
    category = HiddenField('Category')
    submit = SubmitField('Capture')
