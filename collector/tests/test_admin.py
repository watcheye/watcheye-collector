from django.contrib.admin.sites import AdminSite
from django.contrib.auth.models import User
from django.http.request import HttpRequest
from django.test import TestCase

from .. import admin, models


class AlwaysValidFormTests(TestCase):
    """
    Tests AlwaysValidForm customizations.
    """

    def test_validity(self):
        """
        AlwaysValidForm must be always valid as a workaround for inlines
        without change permission not returning all fields.
        """
        form = admin.AlwaysValidForm(data={})
        self.assertTrue(form.is_valid())


class ParameterCollisionForm(TestCase):
    """
    Tests ParameterCollisionForm customizations.
    """

    fixtures = ['collector/tests/fixtures.json']

    def test_restricted_name(self):
        """
        A few names are restricted not to cause tags overriding.
        """
        for parameter in admin.restricted_names:
            with self.subTest(parameter=parameter):
                data = {
                    'group': models.Group.objects.all()[0].name,
                    'name': parameter,
                    'type': models.Parameter.INTEGER,
                    'indexing': True
                }
                form = admin.ParameterCollisionForm(data=data)
                self.assertFalse(form.is_valid())
                self.assertIn('name', form.errors)
                self.assertIn('indexing', form.errors)

    def test_name_collision_with_tag(self):
        """
        Tag names are restricted for indexing parameter not to cause
        tags overriding.
        """
        data = {
            'group': models.Group.objects.all()[0].name,
            'name': models.Tag.objects.all()[0].name,
            'type': models.Parameter.INTEGER,
            'indexing': True
        }
        form = admin.ParameterCollisionForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)
        self.assertIn('indexing', form.errors)

    def test_no_name_collision(self):
        """
        Positive scenario with no name collision.
        """
        data = {
            'group': models.Group.objects.all()[0].name,
            'name': 'bacon',
            'type': models.Parameter.INTEGER,
            'indexing': True
        }
        form = admin.ParameterCollisionForm(data=data)
        self.assertTrue(form.is_valid())

    def test_not_indexing_parameter(self):
        """
        Positive scenario with name collision but parameter is not
        indexing.
        """
        data = {
            'group': models.Group.objects.all()[0].name,
            'name': models.Tag.objects.all()[0].name,
            'type': models.Parameter.INTEGER,
            'indexing': False
        }
        form = admin.ParameterCollisionForm(data=data)
        self.assertTrue(form.is_valid())


class InstanceFormTests(TestCase):
    """
    Tests InstanceForm customizations.
    """

    fixtures = ['collector/tests/fixtures.json']

    def test_empty_oid(self):
        """
        Empty OID should be accepted and replaced with default value.
        """
        host = models.Host.objects.all()[0]
        group = models.Group.objects.filter(type=models.Group.SCALAR)[0]
        data = {
            'host': host.name,
            'group': group.name,
            'oid': '',
            'name': ''
        }
        form = admin.InstanceForm(data=data)
        self.assertTrue(form.is_valid(), form.errors)

    def test_tabular_without_name(self):
        """
        Tabular requires a name.
        """
        host = models.Host.objects.all()[0]
        group = models.Group.objects.filter(type=models.Group.TABULAR)[0]
        data = {
            'host': host.name,
            'group': group.name,
            'oid': 1,
            'name': ''
        }
        form = admin.InstanceForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_tabular_with_name(self):
        """
        Tabular requires a name.
        """
        host = models.Host.objects.all()[0]
        group = models.Group.objects.filter(type=models.Group.TABULAR)[0]
        data = {
            'host': host.name,
            'group': group.name,
            'oid': 1,
            'name': 'spam'
        }
        form = admin.InstanceForm(data=data)
        self.assertTrue(form.is_valid())

    def test_scalar_with_nonzero_oid(self):
        """
        Scalars parameters should have zero OID.
        """
        host = models.Host.objects.all()[0]
        group = models.Group.objects.filter(type=models.Group.SCALAR)[0]
        data = {
            'host': host.name,
            'group': group.name,
            'oid': 1,
            'name': ''
        }
        form = admin.InstanceForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('oid', form.errors)

    def test_scalar_with_name(self):
        """
        Scalar parameters Instance should not have a name.
        """
        host = models.Host.objects.all()[0]
        group = models.Group.objects.filter(type=models.Group.SCALAR)[0]
        data = {
            'host': host.name,
            'group': group.name,
            'oid': 0,
            'name': 'spam'
        }
        form = admin.InstanceForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)

    def test_tabular_with_zero_oid(self):
        """
        Tabular should have nonzero oid.
        """
        host = models.Host.objects.all()[0]
        group = models.Group.objects.filter(type=models.Group.TABULAR)[0]
        data = {
            'host': host.name,
            'group': group.name,
            'oid': 0,
            'name': 'spam'
        }
        form = admin.InstanceForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('oid', form.errors)


class TagFormTests(TestCase):
    """
    Tests TagForm customizations.
    """

    fixtures = ['collector/tests/fixtures.json']

    def test_no_name_collision(self):
        """
        Positive scenario with no name collision.
        """
        form = admin.TagForm(data={'name': 'spam'})
        self.assertTrue(form.is_valid())

    def test_restricted_name(self):
        """
        A few names are restricted not to cause tags overriding.
        """
        for parameter in admin.restricted_names:
            with self.subTest(parameter=parameter):
                data = {'name': parameter}
                form = admin.TagForm(data=data)
                self.assertFalse(form.is_valid())
                self.assertIn('name', form.errors)

    def test_name_collision_with_indexing_parameter(self):
        """
        Indexing parameter names are restricted for tags not to cause
        tags overriding.
        """
        data = {'name': models.Parameter.objects.filter(indexing=True)[0]}
        form = admin.TagForm(data=data)
        self.assertFalse(form.is_valid())
        self.assertIn('name', form.errors)


class HostAdminTests(TestCase):
    """
    Tests HostAdmin customizations.
    """

    fixtures = ['collector/tests/fixtures.json']

    def test_ro_fields_without_object(self):
        """
        Creating new Host object its name should be editable.
        """
        host_admin = admin.HostAdmin(models.Host, AdminSite())
        self.assertNotIn('name', host_admin.get_readonly_fields(object()))

    def test_ro_fields_with_object(self):
        """
        Editing existing Host object its name should not be editable
        because it is used as tag in a InfluxDB measurement.

        https://docs.influxdata.com/influxdb/latest/concepts/key_concepts/
        """
        host = models.Host.objects.all()[0]
        host_admin = admin.HostAdmin(models.Host, AdminSite())
        self.assertIn(
            'name',
            host_admin.get_readonly_fields(object(), obj=host)
        )


class GroupAdminTests(TestCase):
    """
    Tests GroupAdmin customizations.
    """

    fixtures = ['collector/tests/fixtures.json']

    def test_ro_fields_without_object(self):
        """
        Creating new Group object its name should be editable.
        """
        parameter_admin = admin.GroupAdmin(models.Group, AdminSite())
        fields = parameter_admin.get_readonly_fields(object())
        self.assertNotIn('name', fields)

    def test_ro_fields_with_object(self):
        """
        Editing existing Group object its name should not be editable
        because it is used as tag in a InfluxDB measurement.

        https://docs.influxdata.com/influxdb/latest/concepts/key_concepts/
        """
        parameter = models.Parameter.objects.all()[0]
        parameter_admin = admin.GroupAdmin(models.Group, AdminSite())
        fields = parameter_admin.get_readonly_fields(object(), obj=parameter)
        self.assertIn('name', fields)

    def test_in_use(self):
        """
        Tests GroupAdmin.in_use method as custom admin field. It should
        return True if the Group instance has a relation to at least one
        Host object.
        """
        group = models.Group.objects.all()[0]
        group_admin = admin.GroupAdmin(models.Group, AdminSite())
        self.assertTrue(group_admin.in_use(group))

    def test_not_in_use(self):
        """
        Tests GroupAdmin.in_use method as custom admin field. It should
        return False if the Group instance has no relation to any Host
        object.
        """
        group = models.Group.objects.create(name='unused',
                                            type=models.Group.SCALAR)
        group_admin = admin.GroupAdmin(models.Group, AdminSite())
        self.assertFalse(group_admin.in_use(group))


class PermissionsTests(TestCase):
    """
    Tests admin panel permissions.
    """

    fixtures = ['collector/tests/fixtures.json']

    def setUp(self):
        self.user = User.objects.create_superuser(
            username='user',
            email='user@example.com',
            password='pass'
        )

    def test_parameter_inline_permissions(self):
        """
        Existing parameters are listed using dedicated inline. So it
        should not allow to create new parameters, change nor delete
        existing.
        """
        inline = admin.ParameterInline(models.Parameter, AdminSite())
        parameter = models.Parameter.objects.all()[0]
        request = HttpRequest()
        request.user = self.user

        self.assertFalse(inline.has_add_permission(request, parameter))
        self.assertFalse(inline.has_delete_permission(request, parameter))

    def test_add_parameter_inline_permissions(self):
        """
        Parameters are added using dedicated inline. So it should list
        no existing parameters and therefore delete permission is not
        required.
        """
        inline = admin.AddParameterInline(models.Parameter, AdminSite())
        parameter = models.Parameter.objects.all()[0]
        request = HttpRequest()
        request.user = self.user

        self.assertFalse(inline.has_delete_permission(request, parameter))
        self.assertFalse(inline.has_delete_permission(request))

        self.assertEqual(len(inline.get_queryset(request)), 0)

    def test_tag_admin_permissions(self):
        """
        Tags should not be modified and not be listed in admin panel.
        """
        inline = admin.TagAdmin(models.Parameter, AdminSite())
        tag = models.Tag.objects.all()[0]
        request = HttpRequest()
        request.user = self.user

        self.assertFalse(inline.has_change_permission(request, tag))
        self.assertTrue(inline.has_change_permission(request))
        self.assertFalse(inline.has_delete_permission(request, tag))
        self.assertFalse(inline.has_delete_permission(request))

        self.assertEqual(inline.get_model_perms(request), {})
