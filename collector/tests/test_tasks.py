from unittest.mock import MagicMock, patch

from django.test import TestCase, override_settings
from pyasn1.type.char import UTF8String
from pyasn1.type.univ import Integer

from .utils import get_cmd_factory, make_timestamp
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

    def test_aggregator(self):
        """
        Tests if aggregator splits all data into right amount of chunks.
        """
        self.assertEqual(len(list(tasks.aggregator())), 2)

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
        tasks.add_samples('host1', make_timestamp(), [('unknown', 1)])
        self.assertFalse(write_points.called)
        self.assertEqual(logger_warning.call_count, 1)

    @patch('influxdb.InfluxDBClient.write_points')
    def test_exact_parameter(self, write_points):
        """
        Positive scenario test of adding sample to database task.
        """
        tasks.add_samples('host1', make_timestamp(), [('CPU', 1.0)])
        self.assertTrue(write_points.called)

    @patch('collector.tasks.logger.error')
    @patch('influxdb.InfluxDBClient.write_points')
    def test_invalid_value(self, write_points, logger_error):
        """
        Tests if sample with unexpected value type is discarded.
        """
        tasks.add_samples('host1', make_timestamp(), [('CPU', 'a')])
        self.assertFalse(write_points.called)
        self.assertTrue(logger_error.called)


class EmptyDBTasksTests(TestCase):
    def test_aggregator(self):
        """
        Having no hosts nor parameters configured for SMP GET protocol
        aggregator should not fail but return empty iterator.
        """
        self.assertEqual(len(list(tasks.aggregator())), 0)


class TestUnpackDecorator(TestCase):
    def setUp(self):
        self.mock = MagicMock()
        self.func = tasks.unpack(self.mock)

    def test_args(self):
        """
        Tuple of parameters should be converted into call with *args.
        """
        self.func(('ham', 'bacon'))
        self.assertTrue(self.mock.called_with('ham', 'bacon'))

    def test_kwargs(self):
        """
        Dict of parameters should be converted into call with **kwargs.
        """
        self.func({'spam': 'ham', 'eggs': 'bacon'})
        self.assertTrue(self.mock.called_with('ham', 'bacon'))

    def test_regular(self):
        """
        Call with more than one parameter should be left unchanged.
        """
        self.func('spam', 'ham', eggs='bacon')
        self.assertTrue(self.mock.called_with('spam', 'ham', eggs='bacon'))

    def test_regular_single_param(self):
        """
        Call with just one iterable parameter should be left unchanged.
        """
        self.func('spam')
        self.assertTrue(self.mock.called_with('spam'))
