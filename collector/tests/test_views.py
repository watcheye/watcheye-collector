import copy
import json
import uuid
from unittest.mock import patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .utils import DataTestCase
from .. import models


class IndexViewTests(DataTestCase):
    """
    Tests collector:index view.
    """

    def setUp(self):
        self.client = Client()
        self.url = reverse('collector:index')

    @patch('influxdb.InfluxDBClient.write_points')
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_index(self, write_points):
        """
        Positive scenario. HTTP 202 response is expected and so is
        database write for each set of fields and tags.
        """
        response = self.client.post(
            path=self.url,
            data=json.dumps(self.payload),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 202)
        self.assertFalse(response.content)
        self.assertIn('Location', response)
        self.assertTrue(write_points.called)
        self.assertEqual(write_points.call_count, 1)

    def test_not_allowed_methods(self):
        """
        Not allowed HTTP method should be bounced off with
        HTTP 405 Method Not Allowed response and right set of accepted
        methods included its Allow header.
        """
        methods = ['options', 'get', 'head', 'put', 'delete', 'patch', 'trace']

        for method in methods:
            with self.subTest(method=method):
                response = getattr(self.client, method)(path=self.url)
                self.assertEqual(response.status_code, 405)
                self.assertEqual(response['Allow'], 'POST')

    def test_missing_payload_element(self):
        """
        Request with payload having not all required fields should be
        rejected with HTTP 400 Bad Request response.
        """
        data = copy.deepcopy(self.payload_int)
        del data['timestamp']

        response = self.client.post(
            path=self.url,
            data=json.dumps(data),
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)
        self.assertFalse(response.content)

    def test_malformed_json(self):
        """
        Request with payload not in JSON format should be rejected
        with HTTP 400 Bad Request response.
        """
        response = self.client.post(
            path=self.url,
            data='foo',
            content_type='application/json'
        )
        self.assertEqual(response.status_code, 400)

    @patch('collector.tasks.logger.error')
    @patch('influxdb.InfluxDBClient.write_points')
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_missing_host(self, write_points, logger_error):
        """
        Request for unknown host should be accepted but in offline
        processing an error should be logged.
        """
        payload = copy.deepcopy(self.payload)
        payload['host'] = 'unknown'
        self.client.post(
            path=self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertFalse(write_points.called)
        self.assertTrue(logger_error.called)

    @patch('collector.tasks.logger.error')
    @patch('influxdb.InfluxDBClient.write_points')
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_missing_parameter(self, write_points, logger_error):
        """
        Each time full set of parameters should be received. If not an
        error should be logged.
        """
        payload = copy.deepcopy(self.payload)
        payload['samples'].pop()
        self.client.post(
            path=self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertTrue(write_points.called)
        self.assertTrue(logger_error.called)

    @patch('collector.tasks.logger.warning')
    @patch('influxdb.InfluxDBClient.write_points')
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_unknown_parameter(self, write_points, logger_warning):
        """
        Received not configured parameter cannot be process therefore
        warning should be logged.
        """
        payload = copy.deepcopy(self.payload)
        payload['samples'].append({'parameter': 'unknown', 'value': 1})
        self.client.post(
            path=self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertTrue(write_points.called)
        self.assertTrue(logger_warning.called)

    @patch('collector.tasks.logger.error')
    @patch('influxdb.InfluxDBClient.write_points')
    @override_settings(CELERY_TASK_ALWAYS_EAGER=True)
    def test_uncastable_tag(self, write_points, logger_error):
        """
        Received indexing parameter of a wrong type should log an alarm.
        """
        group = models.Group.objects.create(name='spam',
                                            type=models.Group.SCALAR)
        models.Parameter.objects.create(
            group=group,
            name='bacon',
            type=models.Parameter.INTEGER,
            indexing=True
        )
        models.Instance.objects.create(
            group=group,
            host_id=self.hostname
        )
        payload = copy.deepcopy(self.payload)
        payload['samples'].append({'parameter': 'bacon', 'value': 'egg'})
        self.client.post(
            path=self.url,
            data=json.dumps(payload),
            content_type='application/json'
        )
        self.assertTrue(write_points.called)
        self.assertTrue(logger_error.called)


class JobViewTests(TestCase):
    """
    Tests collector:job view.
    """

    def test_job(self):
        """
        Quite simple positive scenario just to verify response format.
        """
        url = reverse('collector:job', kwargs={'uuid': str(uuid.uuid4())})
        client = Client()
        response = client.get(url)
        self.assertEqual(response.status_code, 200)
        self.assertEqual(response['content-type'], 'application/json')
        content = json.loads(response.content.decode())
        self.assertIn('uuid', content)
        self.assertIn('state', content)
