from unittest.mock import patch

from django.test import TestCase, override_settings
from pyasn1.type.char import UTF8String
from pyasn1.type.univ import Integer

from .utils import get_cmd_factory
from .. import tasks


class TasksTests(TestCase):
    fixtures = ['collector/tests/fixtures.json']

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch('collector.tasks.getCmd',
           side_effect=get_cmd_factory(Integer, 1))
    @patch('influxdb.InfluxDBClient.write_points')
    def test_snmp_scheduler_positive_scenario(self, write_points, get_cmd):
        """
        Tests if snmp_scheduler starts tasks chain to the very last
        link.
        """
        tasks.snmp_scheduler()
        self.assertEqual(get_cmd.call_count, 2)
        self.assertEqual(write_points.call_count, 2)

    def test_chunks(self):
        """
        Tests if chunks iterator splits all data into right amount of
        chunks.
        """
        vector = ['spam'] * (tasks.SNMP_MAX_PARAMETERS_IN_QUERY + 1)
        self.assertEqual(len(list(tasks.chunks(vector))), 2)

    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    @patch('collector.tasks.getCmd',
           side_effect=get_cmd_factory(UTF8String, 'a'))
    @patch('influxdb.InfluxDBClient.write_points')
    def test_invalid_value_in_response(self, write_points, get_cmd):
        """
        Tests if received parameter with unexpected type of value
        won't be inserted into database.
        """
        tasks.snmp_scheduler()
        self.assertEqual(get_cmd.call_count, 2)
        self.assertEqual(write_points.call_count, 0)

    @patch('collector.tasks.logger.warning')
    @patch('influxdb.InfluxDBClient.write_points')
    def test_unknown_parameter(self, write_points, logger_warning):
        """
        Tests if unrecognized parameter is discarded.
        """
        tasks.add_samples([[('unknown', 1)]], 'host1')
        self.assertFalse(write_points.called)
        self.assertEqual(logger_warning.call_count, 1)

    @patch('influxdb.InfluxDBClient.write_points')
    def test_exact_parameter(self, write_points):
        """
        Positive scenario test of adding sample to database task.
        """
        tasks.add_samples(
            [[('1.3.6.1.2.1.6.9.0', 0), ('1.3.6.1.2.1.6.12.0', 0)]],
            'host1'
        )
        self.assertTrue(write_points.called)

    @patch('collector.tasks.logger.error')
    @patch('influxdb.InfluxDBClient.write_points')
    def test_invalid_value(self, write_points, logger_error):
        """
        Tests if sample with unexpected value type is discarded.
        """
        tasks.add_samples([[('1.3.6.1.2.1.6.9.0', 'a')]], 'host1')
        self.assertFalse(write_points.called)
        self.assertTrue(logger_error.called)


class EmptyDBTasksTests(TestCase):
    def test_aggregator(self):
        """
        Having no hosts nor parameters configured for SMP GET protocol
        aggregator should not fail but return empty iterator.
        """
        self.assertEqual(len(list(tasks.aggregator())), 0)
