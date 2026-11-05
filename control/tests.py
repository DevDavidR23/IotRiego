import json
from unittest.mock import patch

import requests
from django.contrib.auth.models import AnonymousUser, User
from django.test import RequestFactory, SimpleTestCase, override_settings

from . import services, views

NODERED_SETTINGS = {
    'NODERED_BASE_URL': 'https://node-red.test',
    'NODERED_TIMEOUT': 5,
}


@override_settings(**NODERED_SETTINGS)
class NodeRedServiceTests(SimpleTestCase):
    @patch('control.services.requests.post')
    def test_send_command_posts_valid_payload(self, mock_post):
        mock_post.return_value.status_code = 200
        mock_post.return_value.json.return_value = {'ok': True}

        result = services.send_command('bomba', 'ON')

        self.assertEqual(result['payload'], {'dispositivo': 'bomba', 'estado': 'ON'})
        mock_post.assert_called_once()
        args, kwargs = mock_post.call_args
        self.assertEqual(args[0], 'https://node-red.test/control')
        self.assertEqual(kwargs['json'], {'dispositivo': 'bomba', 'estado': 'ON'})
        self.assertEqual(kwargs['timeout'], 5)

    def test_send_command_rejects_unknown_device(self):
        with self.assertRaises(ValueError):
            services.send_command('ventilador', 'ON')

    def test_send_command_rejects_unknown_state(self):
        with self.assertRaises(ValueError):
            services.send_command('bomba', 'MAYBE')

    @patch('control.services.requests.get')
    def test_check_health_returns_body(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {'status': 'ok'}

        self.assertEqual(services.check_health(), {'status': 'ok'})

    @patch('control.services.requests.get')
    def test_check_health_rejects_unhealthy_body(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {'status': 'down'}

        with self.assertRaises(services.NodeRedResponseError):
            services.check_health()


@override_settings(**NODERED_SETTINGS)
class ControlDeviceViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.staff = User(is_staff=True, is_active=True)

    def _post(self, payload, user=None):
        request = self.factory.post(
            '/api/control/',
            data=json.dumps(payload),
            content_type='application/json',
        )
        request.user = self.staff if user is None else user
        return views.control_device(request)

    def _payload(self, response):
        return json.loads(response.content)

    @patch('control.services.requests.post')
    def test_turn_on_pump(self, mock_post):
        mock_post.return_value.status_code = 200

        response = self._post({'dispositivo': 'bomba', 'estado': 'ON'})

        self.assertEqual(response.status_code, 202)
        self.assertEqual(self._payload(response)['status'], 'accepted')
        self.assertEqual(
            mock_post.call_args.kwargs['json'],
            {'dispositivo': 'bomba', 'estado': 'ON'},
        )

    @patch('control.services.requests.post')
    def test_turn_off_pump(self, mock_post):
        mock_post.return_value.status_code = 200

        response = self._post({'dispositivo': 'bomba', 'estado': 'OFF'})

        self.assertEqual(response.status_code, 202)
        self.assertEqual(
            mock_post.call_args.kwargs['json'],
            {'dispositivo': 'bomba', 'estado': 'OFF'},
        )

    @patch('control.services.requests.post')
    def test_turn_on_sensor(self, mock_post):
        mock_post.return_value.status_code = 200

        response = self._post({'dispositivo': 'sensor', 'estado': 'ON'})

        self.assertEqual(response.status_code, 202)
        self.assertEqual(
            mock_post.call_args.kwargs['json'],
            {'dispositivo': 'sensor', 'estado': 'ON'},
        )

    @patch('control.services.requests.post')
    def test_turn_off_sensor(self, mock_post):
        mock_post.return_value.status_code = 200

        response = self._post({'dispositivo': 'sensor', 'estado': 'OFF'})

        self.assertEqual(response.status_code, 202)
        self.assertEqual(
            mock_post.call_args.kwargs['json'],
            {'dispositivo': 'sensor', 'estado': 'OFF'},
        )

    @patch('control.services.requests.post')
    def test_invalid_device(self, mock_post):
        response = self._post({'dispositivo': 'ventilador', 'estado': 'ON'})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self._payload(response)['code'], 'invalid_device')
        mock_post.assert_not_called()

    @patch('control.services.requests.post')
    def test_invalid_state(self, mock_post):
        response = self._post({'dispositivo': 'bomba', 'estado': 'MAYBE'})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self._payload(response)['code'], 'invalid_state')
        mock_post.assert_not_called()

    @patch('control.services.requests.post')
    def test_invalid_types(self, mock_post):
        response = self._post({'dispositivo': 1, 'estado': True})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self._payload(response)['code'], 'invalid_device')
        mock_post.assert_not_called()

    @patch('control.services.requests.post')
    def test_missing_body(self, mock_post):
        response = self._post({})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self._payload(response)['code'], 'missing_fields')
        mock_post.assert_not_called()

    @patch('control.services.requests.post')
    def test_incomplete_body(self, mock_post):
        response = self._post({'dispositivo': 'bomba'})

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self._payload(response)['code'], 'missing_fields')
        mock_post.assert_not_called()

    @patch('control.services.requests.post')
    def test_rejects_extra_fields_and_topics(self, mock_post):
        response = self._post({
            'dispositivo': 'bomba',
            'estado': 'ON',
            'topic': 'esp32/suelo/bomba/control',
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self._payload(response)['code'], 'invalid_fields')
        mock_post.assert_not_called()

    @patch('control.services.requests.post')
    def test_invalid_json(self, mock_post):
        request = self.factory.post(
            '/api/control/',
            data='no-es-json',
            content_type='application/json',
        )
        request.user = self.staff

        response = views.control_device(request)

        self.assertEqual(response.status_code, 400)
        self.assertEqual(self._payload(response)['code'], 'invalid_json')
        mock_post.assert_not_called()

    @patch('control.services.requests.post')
    def test_node_red_unavailable(self, mock_post):
        mock_post.side_effect = requests.ConnectionError('sin conexion')

        response = self._post({'dispositivo': 'bomba', 'estado': 'ON'})

        self.assertEqual(response.status_code, 503)
        self.assertEqual(self._payload(response)['code'], 'node_red_unavailable')

    @patch('control.services.requests.post')
    def test_node_red_timeout(self, mock_post):
        mock_post.side_effect = requests.Timeout('timeout')

        response = self._post({'dispositivo': 'bomba', 'estado': 'ON'})

        self.assertEqual(response.status_code, 504)
        self.assertEqual(self._payload(response)['code'], 'node_red_timeout')

    @patch('control.services.requests.post')
    def test_node_red_http_error(self, mock_post):
        mock_post.return_value.status_code = 500

        response = self._post({'dispositivo': 'bomba', 'estado': 'ON'})

        self.assertEqual(response.status_code, 502)
        self.assertEqual(self._payload(response)['code'], 'node_red_error')

    @patch('control.services.requests.post')
    def test_user_without_permissions(self, mock_post):
        user = User(is_staff=False, is_active=True)

        response = self._post(
            {'dispositivo': 'bomba', 'estado': 'ON'},
            user=user,
        )

        self.assertEqual(response.status_code, 403)
        self.assertEqual(self._payload(response)['code'], 'forbidden')
        mock_post.assert_not_called()

    @patch('control.services.requests.post')
    def test_anonymous_user(self, mock_post):
        response = self._post(
            {'dispositivo': 'bomba', 'estado': 'ON'},
            user=AnonymousUser(),
        )

        self.assertEqual(response.status_code, 403)
        mock_post.assert_not_called()

    @patch('control.services.requests.post')
    def test_inactive_staff_user(self, mock_post):
        user = User(is_staff=True, is_active=False)

        response = self._post(
            {'dispositivo': 'bomba', 'estado': 'ON'},
            user=user,
        )

        self.assertEqual(response.status_code, 403)
        mock_post.assert_not_called()

    def test_view_keeps_csrf_protection(self):
        self.assertFalse(getattr(views.control_device, 'csrf_exempt', False))


@override_settings(**NODERED_SETTINGS)
class ControlHealthViewTests(SimpleTestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.user = User(is_staff=False, is_active=True)

    def _get(self, user=None):
        request = self.factory.get('/api/control/health/')
        request.user = self.user if user is None else user
        return views.control_health(request)

    @patch('control.services.requests.get')
    def test_health_available(self, mock_get):
        mock_get.return_value.status_code = 200
        mock_get.return_value.json.return_value = {'status': 'ok'}

        response = self._get()

        self.assertEqual(response.status_code, 200)
        self.assertEqual(json.loads(response.content)['status'], 'ok')

    @patch('control.services.requests.get')
    def test_health_unavailable(self, mock_get):
        mock_get.side_effect = requests.ConnectionError('sin conexion')

        response = self._get()

        self.assertEqual(response.status_code, 503)
        self.assertEqual(json.loads(response.content)['code'], 'node_red_unavailable')

    @patch('control.services.requests.get')
    def test_health_timeout(self, mock_get):
        mock_get.side_effect = requests.Timeout('timeout')

        response = self._get()

        self.assertEqual(response.status_code, 504)
        self.assertEqual(json.loads(response.content)['code'], 'node_red_timeout')

    @patch('control.services.requests.get')
    def test_health_error_response(self, mock_get):
        mock_get.return_value.status_code = 500

        response = self._get()

        self.assertEqual(response.status_code, 502)
        self.assertEqual(json.loads(response.content)['code'], 'node_red_error')

    @patch('control.services.requests.get')
    def test_health_requires_authentication(self, mock_get):
        response = self._get(user=AnonymousUser())

        self.assertEqual(response.status_code, 403)
        mock_get.assert_not_called()

    @override_settings(NODERED_BASE_URL='')
    @patch('control.services.requests.get')
    def test_health_not_configured(self, mock_get):
        response = self._get()

        self.assertEqual(response.status_code, 500)
        self.assertEqual(
            json.loads(response.content)['code'],
            'node_red_not_configured',
        )
        mock_get.assert_not_called()
