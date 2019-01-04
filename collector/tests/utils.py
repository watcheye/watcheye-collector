import datetime

from django.test import TestCase
from pysnmp.hlapi import ObjectIdentity, ObjectType

from .. import constants, models


def make_timestamp() -> float:
    """
    Calculates current time as numbers of seconds since epoch.

    :return: timestamp
    """
    return (datetime.datetime.utcnow() - constants.EPOCH).total_seconds()


class DataTestCase(TestCase):
    """
    Base class for test requiring fixtures and/or payloads.
    """
    fixtures = ['collector/tests/fixtures.json']

    @classmethod
    def setUpTestData(cls):
        cls.hostname = 'host1'
        host = models.Host.objects.get(name=cls.hostname)

        base_payload = {
            'host': cls.hostname,
            'timestamp': make_timestamp()
        }

        cls.payload = dict(base_payload)
        cls.payload['samples'] = [
            {
                'parameter': parameter.name,
                'instance': instance.name,
                'value': 1
            }
            for instance in host.instances.all()
            for parameter in instance.group.parameters.all()
        ]

        cls.payload_int = dict(base_payload)
        cls.payload_int['samples'] = [
            {
                'parameter': 'CPU',
                'value': 10
            }
        ]

        cls.payload_float = dict(base_payload)
        cls.payload_float['samples'] = [
            {
                'parameter': 'CPU',
                'value': 10.1
            }
        ]

        cls.payload_bool = dict(base_payload)
        cls.payload_bool['samples'] = [
            {
                'parameter': 'CPU',
                'value': True
            }
        ]

        cls.payload_str = dict(base_payload)
        cls.payload_str['samples'] = [
            {
                'parameter': 'CPU',
                'value': 'spam'
            }
        ]

        cls.payload_array = dict(base_payload)
        cls.payload_array['samples'] = [
            {
                'parameter': 'CPU',
                'value': ['spam', 'ham', 'egg']
            }
        ]


def get_cmd_factory(cls, value):
    """
    A function factory producing replacements for pysnmp.hlapi.getCmd.
    Its products are used in tests to decouple testing from external
    entities by mimicking SNMP GET results normally fetched over the
    network. All SNMP objects are of cls type and have value of value.

    :param cls: expected type of SNMP object
    :param value: expected value of SNMP object
    :return: a callable with same API as pysnmp.hlapi.getCmd
    """
    def wrapper(_snmp_engine, _auth_data, _transport_target, _context_data,
                *var_binds, **_options):
        """
        Ignores all parameters but var_binds and returns it updated with
        value. Accepts same arguments and returns similar result as
        pysnmp.hlapi.getCmd.

        :param _snmp_engine: ignored parameter
        :param _auth_data: ignored parameter
        :param _transport_target: ignored parameter
        :param _context_data: ignored parameter
        :param var_binds: tuple of parameters
        :param _options: ignored parameter
        :return: same as pysnmp.hlapi.getCmd
        """
        def make_value(parameter):
            """
            Takes given parameter and returns it recreated and filled in
            with value.

            :param parameter: SNMP parameter
            :return: SNMP parameter with value
            """
            parameter._ObjectType__state = ObjectType.stClean
            parameter._ObjectType__args[0].__stage = ObjectIdentity.stClean
            identity, _value = parameter
            oid = str(identity._ObjectIdentity__args[0])
            identity = ObjectIdentity(oid)
            identity._ObjectIdentity__oid = oid
            identity._ObjectIdentity__state = ObjectIdentity.stClean
            val = ObjectType(identity, cls(value))
            val._ObjectType__state = ObjectType.stClean
            return val

        return iter(
            [[None, 0, 0, [make_value(bind) for bind in var_binds]]]
        )
    return wrapper
