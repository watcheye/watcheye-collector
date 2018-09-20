import datetime
import functools
import ipaddress
import typing

from celery import group, shared_task
from celery.utils.log import get_task_logger
from django.conf import settings
from influxdb import InfluxDBClient
from pysnmp.hlapi import (CommunityData, ContextData, ObjectIdentity,
                          ObjectType, SnmpEngine, Udp6TransportTarget,
                          UdpTransportTarget, getCmd)

from .constants import (EPOCH, INFLUXDB_DATABASE, INFLUXDB_MEASUREMENT,
                        INFLUXDB_PORT)
from .models import Host, Parameter

SNMP_MAX_PARAMETERS_IN_QUERY = 8
logger = get_task_logger(__name__)
casters = {
    Parameter.BOOLEAN: bool,
    Parameter.INTEGER: int,
    Parameter.FLOAT: float,
    Parameter.STRING: str
}
t_sample = typing.Union[bool, int, float, str]
t_samples_seq = typing.Sequence[typing.Tuple[str, t_sample]]
t_parameters_seq = typing.Sequence[typing.Tuple[str, str]]


def unpack(func: typing.Callable) -> typing.Callable:
    """
    Celery task decorator allowing conveniently chaining tasks.
    By default result of predecessor is placed as first argument of
    successor's signature. Consider following tasks:

    @task
    def add_and_subtract(x, y):
    return x - y, x + y


    @task
    def multiply(a, b):
        return a * b

    Chaining (add_and_subtract.s(4, 2) | multiply.s()).apply_async() is
    not possible. It would end up with TypeError like calling
    multiply((2, 6)). Argument a instead of int variable gets
    tuple of ints and required argument b is missing.

    By decorating a task with unpack decorator such chaining is
    possible. If predecessor returns a dict kwargs mode is assumed.

    http://docs.celeryproject.org/en/latest/userguide/canvas.html#chains
    """
    @functools.wraps(func)
    def _wrapper(*args, **kwargs):
        if not kwargs and len(args) == 1:
            if isinstance(args[0], tuple):
                return func(*args[0])
            if isinstance(args[0], dict):
                return func(**args[0])
        return func(*args, **kwargs)
    return _wrapper


def aggregator() -> typing.Iterator[dict]:
    """
    Not to overload monitored devices with too many parameters in single
    SNMP GET query all parameters for each host are divided into chunks.
    Size of a chunk is defined by SNMP_MAX_PARAMETERS_IN_QUERY constant.

    :return: dict matching to snmp_harvester arguments
    """
    last_hostname = last_ip = last_port = last_community = None
    buff = []
    queryset = Host.parameters.through.objects.exclude(
        host__community=''
    ).exclude(
        parameter__oid=''
    ).values_list(
        'host__name', 'parameter__name', 'host__ip',
        'host__port', 'host__community', 'parameter__oid'
    ).order_by(
        'host__name'
    )
    for hostname, parameter, ip, port, community, oid in queryset:
        if (hostname != last_hostname or
                len(buff) == SNMP_MAX_PARAMETERS_IN_QUERY) and buff:
            yield {
                'host': last_hostname,
                'ip': last_ip,
                'port': last_port,
                'community': last_community,
                'parameters': buff
            }
            buff = []
        last_hostname = hostname
        last_ip = ip
        last_port = port
        last_community = community
        buff.append([oid, parameter])
    if buff:
        yield {
            'host': last_hostname,
            'ip': last_ip,
            'port': last_port,
            'community': last_community,
            'parameters': buff
        }


@shared_task
def snmp_scheduler():
    """
    Orchestrates parameter gathering and storing results do database.
    Instead of delegating multiple tasks one super task is instantiated
    and such task is scheduled for periodic execution.

    http://docs.celeryproject.org/en/latest/userguide/configuration.html#beat-schedule
    """
    group(
        snmp_harvester.s(**kwargs) | add_samples.s()
        for kwargs in aggregator()
    ).delay()


@shared_task
@unpack
def add_samples(host: str, timestamp: float, samples: t_samples_seq) -> None:
    """
    Inserts multiple samples into database in a single query.

    :param host: host name
    :param timestamp: timestamp as seconds from epoch
    :param samples: list of pairs: parameter name and its value
    """
    mapping = dict(samples)
    fields = {}
    for parameter in Parameter.objects.filter(host__name=host,
                                              name__in=mapping.keys()):
        value = mapping[parameter.name]
        logger.debug(
            '%(timestamp)s %(parameter)s@%(host)s = %(value)s',
            {'host': host, 'parameter': parameter.name,
             'timestamp': timestamp, 'value': value}
        )
        # cast value to the right type
        actual_type = type(value)
        target_type = casters[parameter.type]
        try:
            fields[parameter.name] = target_type(value)
        except (ValueError, TypeError):
            logger.error(
                'Cannot cast %(value)s of %(actual_type)s '
                'to %(target_type)s.',
                {'value': value, 'target_type': target_type.__name__,
                 'actual_type': actual_type.__name__}
            )

    if fields:
        client = InfluxDBClient(
            host=settings.INFLUXDB_HOST,
            port=getattr(settings, 'INFLUXDB_PORT', INFLUXDB_PORT),
            username=settings.INFLUXDB_USERNAME,
            password=settings.INFLUXDB_PASSWORD,
            database=getattr(settings, 'INFLUXDB_DATABASE', INFLUXDB_DATABASE)
        )
        client.write_points(
            [
                {
                    'measurement': getattr(settings, 'INFLUXDB_MEASUREMENT',
                                           INFLUXDB_MEASUREMENT),
                    'time': int(timestamp / 60),
                    'fields': fields
                }
            ],
            time_precision='m',
            tags={
                'host': host,
            }
        )
    not_indexed_fields = set(mapping.keys()) - set(fields.keys())
    if not_indexed_fields:
        logger.warning(
            'Not indexed fields %(fields)s for host %(host)s.',
            {
                'fields': ', '.join(sorted(not_indexed_fields)),
                'host': host
            }
        )


@shared_task
def snmp_harvester(host: str, ip: str, port: int, community: str,
                   parameters: t_parameters_seq) -> dict:
    """
    Fires SNMP GET query at endpoint defined by ip and port. The query
    consists all of oids defined in parameters argument.

    :param host: host name
    :param ip: host IP address
    :param port: SNMP port number
    :param community: community name
    :param parameters: list of corresponding pairs: oid and
      parameter name
    :returns: a dict with name of host, timestamp as seconds from epoch,
      and samples as list of pairs: parameter name and its collected
      value.
    """
    if ipaddress.ip_address(ip).version == 4:
        transport = UdpTransportTarget
    else:
        transport = Udp6TransportTarget
    parameters = dict(parameters)

    result = getCmd(
        SnmpEngine(),
        CommunityData(community, mpModel=1),
        transport((ip, port)),
        ContextData(),
        *[ObjectType(ObjectIdentity(oid)) for oid in parameters.keys()]
    )

    _error_indication, _error_status, _error_index, var_binds = next(result)

    now = datetime.datetime.utcnow().replace(second=0, microsecond=0)
    return {
        'host': host,
        'timestamp': (now - EPOCH).total_seconds(),
        'samples': [
            [parameters[str(name)], value._value] for name, value in var_binds
        ]
    }
