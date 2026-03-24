from flask_wtf import FlaskForm
from wtforms import StringField, SelectField, DateField, SubmitField, HiddenField, TextAreaField
from wtforms.validators import DataRequired, Length, Optional, ValidationError


def validate_url(form, field):
    """Ensure external link starts with http:// or https:// if provided."""
    val = (field.data or '').strip()
    if val and not (val.startswith('http://') or val.startswith('https://')):
        raise ValidationError('Link must start with http:// or https://')


class TaskForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(1, 200)])
    # notes is populated by the Quill editor via a hidden field
    notes = HiddenField('Notes')
    # Populated by radio buttons in the template (work/personal); falls back to 'work' in route
    category = HiddenField('Category')
    status = SelectField(
        'Status (optional)',
        choices=[
            ('Not Started', 'Not Started'),
            ('In Progress', 'In Progress'),
            ('Done', 'Done'),
            ('Blocked', 'Blocked'),
        ],
        validators=[Optional()]
    )
    project_id = SelectField(
        'Project (optional)',
        coerce=lambda x: int(x) if x else None,
        validators=[Optional()]
    )
    due_date = DateField('Due Date (optional)', validators=[Optional()])
    external_link = StringField('External Link (optional)', validators=[Optional(), validate_url])
    estimated_minutes = SelectField(
        'Estimated Time (optional)',
        choices=[
            ('', '— Unknown —'),
            ('15', '15 min'),
            ('30', '30 min'),
            ('60', '1 hr'),
            ('120', '2 hrs'),
            ('180', '3 hrs'),
        ],
        coerce=lambda x: int(x) if x else None,
        validators=[Optional()],
    )
    first_action = StringField(
        'First Physical Action (optional)',
        validators=[Optional(), Length(max=500)],
    )
    submit = SubmitField('Save Task')
