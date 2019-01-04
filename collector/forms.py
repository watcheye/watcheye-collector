import math

from django import forms
from django.core import validators
from django.core.exceptions import ValidationError
from django.utils.translation import gettext as _

from . import constants


class SeriesForm(forms.Form):
    """
    Roughly validates received series of data.
    """
    host = forms.CharField(max_length=constants.NAME_MAX_LENGTH)
    timestamp = forms.FloatField(min_value=0)
    samples = forms.Field()

    def clean_samples(self):
        """
        Cleans samples field. Actually delegates validation
        to SampleForm for each sample.

        :return: list of samples
        :raise: ValidationError
        """
        cleaned = []
        for row in self.data['samples']:
            form = SampleForm(data=row)
            if form.is_valid():
                cleaned.append(form.cleaned_data)
            else:
                raise ValidationError(_('Invalid value.'), code='invalid')
        return cleaned


class SampleForm(forms.Form):
    """
    Roughly validates received data sample.
    """
    parameter = forms.CharField(max_length=constants.NAME_MAX_LENGTH)
    instance = forms.CharField(max_length=constants.NAME_MAX_LENGTH,
                               required=False)
    value = forms.Field(
        validators=[
            validators.ProhibitNullCharactersValidator
        ]
    )

    def clean_value(self):
        """
        Cleans value field and verifies its type. Allowed types are:
        int, float (finite), bool and str.

        :return: unchanged value
        :raise: ValidationError
        """
        value = self.cleaned_data['value']
        if isinstance(value, (int, bool, str)) or \
                (isinstance(value, float) and math.isfinite(value)):
            return value
        raise ValidationError(_('Invalid value.'), code='invalid')
