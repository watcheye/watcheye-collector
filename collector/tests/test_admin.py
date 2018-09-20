from django.contrib.admin.sites import AdminSite
from django.test import TestCase

from .. import admin
from ..models import Host, Parameter


class HostAdminTests(TestCase):
    """
    Tests HostAdmin customizations.
    """

    fixtures = ['collector/tests/fixtures.json']

    def test_ro_fields_without_object(self):
        """
        Creating new Host object its name should be editable.
        """
        host_admin = admin.HostAdmin(Host, AdminSite())
        self.assertNotIn('name', host_admin.get_readonly_fields(object()))

    def test_ro_fields_with_object(self):
        """
        Editing existing Host object its name should not be editable
        because it is used as tag in a InfluxDB measurement.

        https://docs.influxdata.com/influxdb/latest/concepts/key_concepts/
        """
        host = Host.objects.all()[0]
        host_admin = admin.HostAdmin(Host, AdminSite())
        self.assertIn(
            'name',
            host_admin.get_readonly_fields(object(), obj=host)
        )


class ParameterAdminTests(TestCase):
    """
    Tests ParameterAdmin customizations.
    """

    fixtures = ['collector/tests/fixtures.json']

    def test_ro_fields_without_object(self):
        """
        Creating new Parameter object its name and type should be
        editable.
        """
        parameter_admin = admin.ParameterAdmin(Parameter, AdminSite())
        fields = parameter_admin.get_readonly_fields(object())
        self.assertNotIn('name', fields)
        self.assertNotIn('type', fields)

    def test_ro_fields_with_object(self):
        """
        Editing existing Parameter object its name should not be
        editable because it is used as tag in a InfluxDB measurement.

        https://docs.influxdata.com/influxdb/latest/concepts/key_concepts/
        """
        parameter = Parameter.objects.all()[0]
        parameter_admin = admin.ParameterAdmin(Parameter, AdminSite())
        fields = parameter_admin.get_readonly_fields(object(), obj=parameter)
        self.assertIn('name', fields)
        self.assertIn('type', fields)

    def test_delete_permission(self):
        """
        No user should have ability to delete a Parameter because
        it might be recreated with different type causing issues with
        InfluxDB.
        """
        parameter_admin = admin.ParameterAdmin(Host, AdminSite())
        self.assertFalse(parameter_admin.has_delete_permission(object()))

    def test_in_use(self):
        """
        Tests ParameterAdmin.in_use method as custom admin field.
        It should return True if the Parameter instance has a relation
        to at least one Host object.
        """
        parameter = Parameter.objects.all()[0]
        parameter_admin = admin.ParameterAdmin(Host, AdminSite())
        self.assertTrue(parameter_admin.in_use(parameter))

    def test_not_in_use(self):
        """
        Tests ParameterAdmin.in_use method as custom admin field.
        It should return False if the Parameter instance has no relation
        to any Host object.
        """
        parameter = Parameter.objects.create(
            name='unused', type=Parameter.INTEGER
        )
        parameter_admin = admin.ParameterAdmin(Host, AdminSite())
        self.assertFalse(parameter_admin.in_use(parameter))
