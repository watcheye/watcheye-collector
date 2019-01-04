#!/usr/bin/env python

import argparse
import sys

import django
from celery import Celery
from django.conf import settings
from django.test.utils import get_runner


def main():
    # Django setup
    if not settings.configured:
        settings.configure(
            INSTALLED_APPS=[
                'django.contrib.auth',
                'django.contrib.contenttypes',
                'django.contrib.admin',
                'django.contrib.sessions',
                'collector.apps.CollectorConfig'
            ],
            DATABASE_ENGINE='django.db.backends.sqlite3',
            DATABASES={
                'default': {
                    'ENGINE': 'django.db.backends.sqlite3'
                }
            },
            ROOT_URLCONF='test_urls',
            INFLUXDB_HOST='localhost',
            INFLUXDB_USERNAME='user',
            INFLUXDB_PASSWORD='secret',
            CELERY_BROKER_URL='memory://localhost/',
            CELERY_RESULT_BACKEND='rpc://localhost:5672//'
        )

    django.setup()

    # Celery setup
    app = Celery('watcheye')
    app.config_from_object('django.conf:settings', namespace='CELERY')
    app.autodiscover_tasks()

    # tests setup
    test_runner_class = get_runner(settings)
    parser = argparse.ArgumentParser()
    parser.add_argument(
        '-v', '--verbosity',
        action='store',
        dest='verbosity',
        default=1,
        type=int,
        choices=[0, 1, 2, 3],
        help='Verbosity level; 0=minimal output, 1=normal output, '
             '2=verbose output, 3=very verbose output'
    )
    parser.add_argument(
        '--failfast',
        action='store_true',
        help='Tells Django to stop running the test suite '
             'after first failed test.'
    )
    test_runner_class.add_arguments(parser)
    args = parser.parse_args()
    test_runner = test_runner_class(**vars(args))

    failures = test_runner.run_tests(['collector'])

    sys.exit(failures)


if __name__ == '__main__':
    main()
