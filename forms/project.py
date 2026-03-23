from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, SelectField, DateField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, ValidationError


def validate_url(form, field):
    """Ensure external link starts with http:// or https:// if provided."""
    val = (field.data or '').strip()
    if val and not (val.startswith('http://') or val.startswith('https://')):
        raise ValidationError('Link must start with http:// or https://')


class ProjectForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(1, 200)])
    description = TextAreaField('Description', validators=[Optional()])
    big_idea_id = SelectField('Big Idea', coerce=int, validators=[DataRequired()])
    due_date = DateField('Due Date (optional)', validators=[Optional()])
    external_link = StringField('External Link (optional)', validators=[Optional(), validate_url])
    submit = SubmitField('Save Project')
