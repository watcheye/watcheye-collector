import getpass

import influxdb
import influxdb.exceptions
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError

from collector.constants import INFLUXDB_DATABASE, INFLUXDB_PORT


class Command(BaseCommand):
    help = 'InfluxDB batch provisioning.'

    def add_arguments(self, parser) -> None:
        parser.add_argument(
            '--username',
            required=True,
            help='Username of account with admin privileges.'
        )
        parser.add_argument(
            '--password',
            help='Password of account with admin privileges. Omit to enter '
                 'interactive mode which protects it from disclosing.'
        )
        parser.add_argument(
            '--policy',
            help='Retention policy name (default: watcheye).'
        )
        parser.add_argument(
            '--duration',
            help='Retention policy duration (default: 100d).'
        )

    def handle(self, *args: tuple, **options: dict) -> None:
        """
        Connects to InfluxDB instance and creates database, retention
        policy and application user with minimal privileges.

        :param args: positional arguments
        :param options: command line parameters
        :raises: CommandError
        """
        password = options['password'] or getpass.getpass('Password: ')
        database = getattr(settings, 'INFLUXDB_DATABASE', INFLUXDB_DATABASE)
        policy = options['policy'] or \
            getattr(settings, 'INFLUXDB_RETENTION_POLICY', 'watcheye')
        duration = options['duration'] or \
            getattr(settings, 'INFLUXDB_DURATION', '100d')

        client = influxdb.InfluxDBClient(
            host=settings.INFLUXDB_HOST,
            port=getattr(settings, 'INFLUXDB_PORT', INFLUXDB_PORT),
            username=options['username'],
            password=password
        )
        try:
            client.create_database(database)
        except influxdb.exceptions.InfluxDBClientError as e:
            if e.code == 401:
                message = 'Authorization failed.'
            else:
                message = e.content
            raise CommandError(message) from e

        try:
            client.create_retention_policy(
                name=policy,
                duration=duration,
                replication='1',
                database=database,
                default=True
            )
        except influxdb.exceptions.InfluxDBClientError as e:
            if e.content != 'retention policy already exists':
                raise CommandError('Could not create retention policy.') from e

        try:
            client.create_user(
                username=settings.INFLUXDB_USERNAME,
                password=settings.INFLUXDB_PASSWORD
            )
        except influxdb.exceptions.InfluxDBClientError as e:
            if e.content != 'user already exists':
                raise CommandError('Could not create user.') from e

        client.grant_privilege(
            privilege='all',
            database=database,
            username=settings.INFLUXDB_USERNAME
        )
        self.stdout.write(
            self.style.SUCCESS('InfluxDB provisioning successfully completed.')
        )
