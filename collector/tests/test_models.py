from django.test import TestCase

from ..models import Host, Parameter


class ModelTests(TestCase):
    """
    Tests models customizations.
    """

    def test_host_str(self):
        """
        Verifies casting Host object to str.
        """
        host_name = 'test'
        host = Host(
            name=host_name,
            ip='127.0.0.1',
        )
        self.assertEqual(host_name, str(host))

    def test_parameter_str(self):
        """
        Verifies casting Parameter object to str.
        """
        parameter_name = 'CPU'
        parameter = Parameter(
            name=parameter_name,
            type=Parameter.FLOAT
        )
        self.assertEqual(parameter_name, str(parameter))
