from django.utils import timezone

NAME_MAX_LENGTH = 32
OID_MAX_LENGTH = 64
EPOCH = timezone.datetime(1970, 1, 1)
INFLUXDB_PORT = 8086
INFLUXDB_DATABASE = 'watcheye'
INFLUXDB_MEASUREMENT = 'samples'
