import datetime
import ipaddress
import typing

import celery
from celery.utils.log import get_task_logger
from django.conf import settings
from influxdb import InfluxDBClient
from pyasn1.type.univ import Null
from pysnmp.hlapi import (CommunityData, ContextData, ObjectIdentity,
                          ObjectType, SnmpEngine, Udp6TransportTarget,
                          UdpTransportTarget, getCmd)

from .constants import EPOCH, INFLUXDB_DATABASE, INFLUXDB_PORT
from .models import Group, Host, Instance, Parameter

SNMP_MAX_PARAMETERS_IN_QUERY = 32
INFLUXDB_BATCH_SIZE = getattr(settings, 'INFLUXDB_BATCH_SIZE', 10000)
logger = get_task_logger(__name__)
casters = {
    Parameter.BOOLEAN: bool,
    Parameter.INTEGER: int,
    Parameter.FLOAT: float,
    Parameter.STRING: str
}

t_sample_value = typing.Union[bool, int, float, str]

# parameter name, instance name, value
t_http_sample = typing.Tuple[str, str, t_sample_value]

t_http_samples = typing.Sequence[t_http_sample]

# OID, value
t_snmp_sample = typing.Tuple[str, t_sample_value]

# single snmp_harvester task returns just a portion of data
t_snmp_samples_chunk = typing.Sequence[t_snmp_sample]

# group of snmp_harvester tasks returns full set of data
t_snmp_samples = typing.Sequence[t_snmp_samples_chunk]

t_samples = typing.Union[t_http_samples, t_snmp_samples]


def aggregator() -> typing.Iterator[typing.Tuple[str, str, int,
                                                 str, typing.List[str]]]:
    """
    Iterates over hosts producing settings for SNMP query.

    :return: tuple matching to snmp_harvester arguments
    """
    queryset = Host.objects.exclude(
        community=''
    ).prefetch_related(
        'instances', 'instances__group', 'instances__group__parameters'
    )
    for host in queryset:

        parameters = [
            compose_oid(group=instance.group,
                        parameter=parameter,
                        instance=instance)
            for instance in host.instances.all()
            for parameter in instance.group.parameters.all()
            if instance.group.oid
        ]
        if parameters:
            yield host.name, host.ip, host.port, host.community, parameters


def compose_oid(group: Group, parameter: Parameter, instance: Instance) -> str:
    """
    Composes OID or OID-like identifier uniquely identifying a sample.

    :param group: sample's Group object instance
    :param parameter: sample's Parameter object instance
    :param instance: sample's Instance object instance
    :return: sample's identifier
    """
    if group.oid:
        template = '{group.oid}.{parameter.oid}.{instance.oid}'
    else:
        template = '{group.name}:{parameter.name}:{instance.name}'
    return template.format(group=group,
                           parameter=parameter,
                           instance=instance)


def chunks(vector: typing.Sequence) -> typing.Sequence:
    """
    Slices vector into chunks not longer than
    SNMP_MAX_PARAMETERS_IN_QUERY constant.

    :param vector: possibly too long vector to be chopped
    :return: slices of vector
    """
    for i in range(0, len(vector), SNMP_MAX_PARAMETERS_IN_QUERY):
        yield vector[i:i + SNMP_MAX_PARAMETERS_IN_QUERY]


@celery.shared_task
def snmp_scheduler() -> None:
    """
    Orchestrates parameter gathering and storing results to database.
    Instead of delegating multiple tasks one super task is instantiated
    and such task is scheduled for periodic execution.

    http://docs.celeryproject.org/en/latest/userguide/configuration.html#beat-schedule
    """
    celery.group(
        celery.chord(
            (snmp_harvester.s(ip, port, community, parameters_chunk)
             for parameters_chunk in chunks(parameters)),
            add_samples.s(host=host)
        )
        for host, ip, port, community, parameters in aggregator()
    ).delay()


class ResultPacker:
    """
    Packs samples into bundles to be written into the same measurement
    with the same sets of tags.
    """
    def __init__(self, host: Host,
                 mapping: typing.Dict[str, t_sample_value]) -> None:
        """
        Constructor of new ResultPacker objects.

        :param host: Host object which samples belong to.
        :param mapping: maps OID-like sample identifiers to theirs value
        """
        self.host = host
        self.mapping = mapping
        self._global_tags = None

    @classmethod
    def snmp(cls, host: Host, samples: t_snmp_samples):
        """
        Alternative "constructor" for SNMP samples adjusting
        theirs structure before calling actual constructor.

        :param host: Host object which samples belong to.
        :param samples: chunks of SNMP samples
        :return: ResultPacker instance
        """
        mapping = {
            oid: value
            for sample in samples
            for oid, value in sample
        }
        return cls(host, mapping)

    @classmethod
    def http(cls, host: Host, samples: t_http_samples):
        """
        Alternative "constructor" for HTTP samples adjusting
        theirs structure before calling actual constructor.

        :param host: Host object which samples belong to.
        :param samples: chunks of HTTP samples
        :return: ResultPacker instance
        """
        mapping = {}
        samples_tree = {}
        missing = []
        for parameter, instance, value in samples:
            try:
                samples_tree[parameter][instance] = value
            except KeyError:
                samples_tree[parameter] = {instance: value}

        for instance in host.instances.all():
            for parameter in instance.group.parameters.all():
                try:
                    value = samples_tree[parameter.name].pop(instance.name)
                except KeyError:
                    missing.append([parameter.name, instance.name])
                else:
                    oid = compose_oid(
                        group=instance.group,
                        parameter=parameter,
                        instance=instance)
                    mapping[oid] = value
        unknown = [
            [parameter, instance]
            for parameter, instances in samples_tree.items()
            for instance in instances
        ]
        if missing:
            elements = ', '.join('#'.join(row) for row in missing)
            logger.error(
                'Missing samples: {elements}.'.format(elements=elements)
            )
        if unknown:
            elements = ', '.join('#'.join(row) for row in unknown)
            logger.warning(
                'Unknown samples: {elements}.'.format(elements=elements)
            )

        return cls(host, mapping)

    @property
    def global_tags(self) -> typing.Dict[str, t_sample_value]:
        """
        Host specific tags comes from scalar indexing parameters,
        host name and tags themselves.

        :return: tags as name to value mapping
        """
        if self._global_tags is not None:
            return self._global_tags
        tags = {tag_value.tag_id: tag_value.value
                for tag_value in self.host.tag_values.all()}
        tags['host'] = self.host.name
        for instance in self.host.instances.all():
            if instance.group.type == Group.SCALAR:
                tags.update(self.values_for_instance(instance, True))
        self._global_tags = tags
        return tags

    def tags(self, instance) -> typing.Dict[str, t_sample_value]:
        """
        Instance specific tags - host tags enriched with instance name
        and tabular indexing parameters.

        :param instance: Host's parameters Instance object
        :return: tags as name to value mapping
        """
        t = dict(self.global_tags)
        if instance.group.type == Group.TABULAR:
            t.update(self.values_for_instance(instance, True))
            t['instance'] = instance.name
        return t

    def fields(self, instance) -> typing.Dict[str, t_sample_value]:
        """
        Instance specific fields - samples which are not considered as
        indexing parameters.

        :param instance: Host's parameters Instance object
        :return: fields as name to value mapping
        """
        return dict(self.values_for_instance(instance, False))

    def values_for_instance(self, instance: Instance,
                            indexing: bool) -> typing.Iterator[t_snmp_sample]:
        """
        Iterates through parameters of given instance and casts
        gathered values.

        :param instance: process parameters for this instance only
        :param indexing: process indexing or non-indexing parameters
        :return: tuple of parameter name and value
        """
        for parameter in instance.group.parameters.all():
            oid = compose_oid(
                group=instance.group,
                parameter=parameter,
                instance=instance
            )
            if oid in self.mapping and parameter.indexing == indexing:
                value = self.mapping.pop(oid)
                target_type = casters[parameter.type]

                try:
                    yield parameter.name, target_type(value)
                except (ValueError, TypeError):
                    logger.error(
                        'Cannot cast %(value)s of %(actual_type)s '
                        'to %(target_type)s.',
                        {
                            'value': value,
                            'target_type': target_type.__name__,
                            'actual_type': type(value).__name__
                        }
                    )


@celery.shared_task
def add_samples(samples: t_samples, host: str, mode: bool = True,
                timestamp: float = None) -> None:
    """
    Inserts multiple samples into database in a single query.

    :param host: host name
    :param samples: list of pairs: parameter name and its value
    :param mode: indicates origin of samples: True - SNMP, False - HTTP
    :param timestamp: timestamp as seconds from epoch
    """
    try:
        host = Host.objects.prefetch_related(
            'tag_values', 'instances', 'instances__group',
            'instances__group__parameters'
        ).get(name=host)
    except Host.DoesNotExist:
        logger.error('Host {host} was not found.'.format(host=host))
        return

    if timestamp is None:
        timestamp = (datetime.datetime.utcnow() - EPOCH).total_seconds()
    if mode:
        packer = ResultPacker.snmp(host, samples)
    else:
        packer = ResultPacker.http(host, samples)

    client = InfluxDBClient(
        host=settings.INFLUXDB_HOST,
        port=getattr(settings, 'INFLUXDB_PORT', INFLUXDB_PORT),
        username=settings.INFLUXDB_USERNAME,
        password=settings.INFLUXDB_PASSWORD,
        database=getattr(settings, 'INFLUXDB_DATABASE', INFLUXDB_DATABASE)
    )

    tt = int(timestamp / 60)
    points = []
    for instance in host.instances.all():
        fields = packer.fields(instance)
        tags = packer.tags(instance)
        if fields:
            points.append(
                {
                    'measurement': instance.group.name,
                    'time': tt,
                    'fields': fields,
                    'tags': tags
                }
            )
    if points:
        client.write_points(
            points=points,
            time_precision='m',
            batch_size=INFLUXDB_BATCH_SIZE
        )

    not_indexed_fields = set(packer.mapping.keys())
    if not_indexed_fields:
        logger.warning(
            'Not indexed fields %(fields)s for host %(host)s.',
            {
                'fields': ', '.join(not_indexed_fields),
                'host': host
            }
        )


@celery.shared_task
def snmp_harvester(ip: str, port: int, community: str,
                   parameters: typing.Iterable[str]) -> t_snmp_samples_chunk:
    """
    Fires SNMP GET query at endpoint defined by ip and port. The query
    consists all of OIDs defined in parameters argument.

    :param ip: host IP address
    :param port: SNMP port number
    :param community: community name
    :param parameters: list of OIDs
    :returns: samples as list of pairs: OID and its collected value
    """
    if ipaddress.ip_address(ip).version == 4:
        transport = UdpTransportTarget
    else:
        transport = Udp6TransportTarget

    result = getCmd(
        SnmpEngine(),
        CommunityData(community, mpModel=1),
        transport((ip, port)),
        ContextData(),
        *[ObjectType(ObjectIdentity(oid)) for oid in parameters]
    )

    _error_indication, _error_status, _error_index, var_binds = next(result)

    return [
        (str(name), value._value)
        for name, value in var_binds
        if not isinstance(value, Null)
    ]
