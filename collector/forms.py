import math

from django import forms
from django.core import validators
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from . import constants


class SampleForm(forms.Form):
    """
    Roughly validates received sample data.
    """
    host = forms.CharField(max_length=constants.NAME_MAX_LENGTH)
    parameter = forms.CharField(max_length=constants.NAME_MAX_LENGTH)
    timestamp = forms.FloatField(min_value=0)
    value = forms.Field(
        validators=[
            validators.ProhibitNullCharactersValidator,

        ]
    )

    def clean_value(self):
        """
        Cleans value field and verifies it's type. Allowed types are:
        int, float (finite), bool and str.

        :return: unchanged value
        :raise: ValidationError
        """
        value = self.cleaned_data['value']
        if isinstance(value, (int, bool, str)) or \
                (isinstance(value, float) and math.isfinite(value)):
            return value
        raise ValidationError(_('Invalid value.'), code='invalid')
