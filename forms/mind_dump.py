from flask_wtf import FlaskForm
from wtforms import StringField, SubmitField, HiddenField, TextAreaField
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


class EditMindDumpForm(FlaskForm):
    """Form for editing an existing mind dump entry."""
    content = TextAreaField(
        'Content',
        validators=[DataRequired(), Length(1, 1000)],
        render_kw={'rows': 4},
    )
    category = HiddenField('Category')
    submit = SubmitField('Save Changes')
