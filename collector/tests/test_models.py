from django.test import TestCase

from ..models import Group, Host, Instance, Parameter, Tag, TagValue


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
            ip='127.0.0.1'
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

    def test_tag_str(self):
        """
        Verifies casting Tag object to str.
        """
        host = Host(
            name='test',
            ip='127.0.0.1'
        )
        host.save()
        name = 'spam'
        value = 'ham'
        tag = Tag(name=name)
        tag_value = TagValue(tag=tag, host=host, value=value)
        self.assertEqual(name, str(tag))
        self.assertEqual(
            '{name} = {value}'.format(name=name, value=value),
            str(tag_value)
        )

    def test_group_str(self):
        """
        Verifies casting Group object to str.
        """
        name = 'test'
        group = Group(name=name, type=Group.SCALAR)
        self.assertEqual(name, str(group))

    def test_instance_str(self):
        """
        Verifies casting Instance object to str.
        """
        instance_name = 'test_instance'
        group_name = 'test_group'
        group = Group.objects.create(name=group_name, type=Group.SCALAR)
        host = Host.objects.create(name='test_host', ip='127.0.0.1')
        instance = Instance(group=group, host=host, name=instance_name)
        self.assertEqual(
            '{instance_name}@{group_name}'.format(
                instance_name=instance_name, group_name=group_name
            ),
            str(instance)
        )
