import re
from flask_wtf import FlaskForm
from wtforms import StringField, TextAreaField, HiddenField, SubmitField
from wtforms.validators import DataRequired, Length, Optional, ValidationError


def validate_hex_color(form, field):
    if field.data and not re.match(r'^#[0-9A-Fa-f]{6}$', field.data):
        raise ValidationError('Must be a valid 6-digit hex color (e.g. #6366f1).')


class BigIdeaForm(FlaskForm):
    title = StringField('Title', validators=[DataRequired(), Length(1, 200)])
    description = TextAreaField('Description', validators=[Optional()])
    # Populated by radio buttons in the template (work/personal); falls back to 'work' in route
    category = HiddenField('Category')
    accent_color = StringField(
        'Accent Color',
        validators=[Optional(), validate_hex_color],
        default='#6366f1'
    )
    submit = SubmitField('Save')
