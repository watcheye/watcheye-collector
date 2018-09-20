from .utils import DataTestCase
from .. import forms


class SampleFormTests(DataTestCase):
    """
    Tests form validity especially taking into account
    its clean_value method.
    """

    def test_form(self):
        """
        Tests form against payloads with values of all supported types.
        Neither value nor its type should be changed during validation.
        """
        for payload in [
            self.payload_int,
            self.payload_float,
            self.payload_bool,
            self.payload_str
        ]:
            with self.subTest(value=payload['value']):
                form = forms.SampleForm(data=payload)
                self.assertTrue(form.is_valid())
                cleaned_value = form.cleaned_data['value']
                value = payload['value']
                self.assertEqual(value, cleaned_value)
                self.assertEqual(type(cleaned_value), type(value))

    def test_form_wrong_type(self):
        """
        Tests form against payload with nonempty value of unsupported
        type.
        """
        form = forms.SampleForm(data=self.payload_array)
        self.assertFalse(form.is_valid())
