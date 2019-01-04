.. image:: https://img.shields.io/travis/com/watcheye/watcheye-collector.svg
    :alt: Travis (.com)
    :target: https://travis-ci.com/watcheye/watcheye-collector
.. image:: https://img.shields.io/coveralls/github/watcheye/watcheye-collector.svg
    :target: https://coveralls.io/github/watcheye/watcheye-collector
.. image:: https://img.shields.io/pypi/v/watcheye-collector.svg
    :target: https://pypi.python.org/pypi/watcheye-collector
.. image:: https://img.shields.io/pypi/format/watcheye-collector.svg
    :target: https://pypi.python.org/pypi/watcheye-collector
.. image:: https://img.shields.io/pypi/djversions/watcheye-collector.svg
    :target: https://pypi.python.org/pypi/watcheye-collector
.. image:: https://img.shields.io/pypi/pyversions/watcheye-collector.svg
    :target: https://pypi.python.org/pypi/watcheye-collector
.. image:: https://img.shields.io/pypi/status/watcheye-collector.svg
    :target: https://pypi.python.org/pypi/watcheye-collector
.. image:: https://img.shields.io/github/license/watcheye/watcheye-collector.svg

=========
Collector
=========

Collector is a Django application to collect monitoring data samples
through HTTP or SNMP GET interface. Collected data might be then
visualized using e.g. `Grafana <https://grafana.com/grafana/download>`_.

Dependencies
------------

Collector uses `InfluxDB <https://portal.influxdata.com/downloads>`_
time series database for storing monitoring data samples and `django
supported database
<https://docs.djangoproject.com/en/dev/ref/databases/>`_ for storing
configuration and
`Redis broker
<http://docs.celeryproject.org/en/latest/getting-started/brokers/redis.html>`_.

Quick start
-----------

Assuming InfluxDB is properly configured (`setting up authentication
<https://docs.influxdata.com/influxdb/latest/administration/authentication_and_authorization/#set-up-authentication>`_
is recommended) and so is Redis broker just a few steps are required.

#. Install ``watcheye-collector``:

   .. code:: shell

      $ pip install watcheye-collector

#. Add ``collector`` application to ``INSTALLED_APPS`` setting.

   .. code:: python

      INSTALLED_APPS = [
          ...
          'collector',
      ]

#. Integrate Celery with your django project (see `Celery documentation
   <http://docs.celeryproject.org/en/latest/django/first-steps-with-django.html>`_
   for further reference).

#. Add InfluxDB connection and Celery configuration in ``settings.py``
   file:

   .. code:: python

      INFLUXDB_HOST = 'my_host'
      INFLUXDB_USERNAME = 'user'
      INFLUXDB_PASSWORD = 'secret'

      CELERY_BEAT_SCHEDULE = {
          'snmp-scheduler': {
              'task': 'collector.tasks.snmp_scheduler',
              'schedule': crontab(minute='*')
          }
      }
      CELERY_RESULT_BACKEND = 'redis://my_broker_host/0'
      CELERY_BROKER_URL = 'redis://my_broker_host/1'

      # to use non-default values configure also:
      INFLUXDB_PORT = 1234
      INFLUXDB_DATABASE = 'my_database'
      INFLUXDB_RETENTION_POLICY = 'my_policy'
      INFLUXDB_DURATION = '30d'

#. To set InfluxDB instance up run:

   .. code:: shell

      python manage.py setupinfluxdb --username <admin_username>

#. To create the collector models run:

   .. code:: shell

      python manage.py migrate

#. Include the collector URLconf in your project urls.py:

   .. code:: python

      path('collector/', include('collector.urls')),

#. Start the development server and visit http://127.0.0.1:8000/admin/
   to create a collector configuration (the Admin application must also
   be enabled).

#. Run Celery worker with:

   .. code:: shell

      celery --beat --app <my_project> worker

#. POST some samples:

   .. code:: shell

      $ curl -i -X POST \
      -H "Content-Type: application/json" \
      -d '{"host":"test", "timestamp": 1500000000,
      "samples": [{"parameter":"CPU", "value": 10}]}' \
      http://127.0.0.1:8000/collector/
