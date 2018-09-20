import json
import uuid
from unittest.mock import patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse

from .utils import DataTestCase


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
        response = self.client.post(
            path=self.url,
            data=json.dumps(self.payload_int),
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
        data = dict(self.payload_int)
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
