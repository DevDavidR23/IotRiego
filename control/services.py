"""Capa de servicios para la comunicacion con la API HTTP de Node-RED.

Node-RED es el unico componente que habla MQTT con el ESP32. Django nunca
publica directamente en el broker ni conoce los topics: solo envia los
comandos validados a los endpoints /health y /control.
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

VALID_DEVICES = frozenset({'bomba', 'sensor'})
VALID_STATES = frozenset({'ON', 'OFF'})

HEALTH_PATH = '/health'
CONTROL_PATH = '/control'
MOTOR_PATH = '/motor'
SENSOR_PATH = '/sensor/leer'


class NodeRedError(Exception):
    """Error base de comunicacion con Node-RED."""


class NodeRedNotConfigured(NodeRedError):
    """Falta configurar NODERED_BASE_URL."""


class NodeRedUnavailable(NodeRedError):
    """No fue posible establecer conexion con Node-RED."""


class NodeRedTimeout(NodeRedError):
    """Node-RED no respondio dentro del tiempo configurado."""


class NodeRedResponseError(NodeRedError):
    """Node-RED respondio con un estado HTTP o cuerpo inesperado."""


def _base_url():
    base_url = (getattr(settings, 'NODERED_BASE_URL', '') or '').rstrip('/')
    if not base_url:
        raise NodeRedNotConfigured(
            'Configura NODERED_BASE_URL en las variables de entorno.'
        )
    return base_url


def _timeout():
    try:
        return float(getattr(settings, 'NODERED_TIMEOUT', 5))
    except (TypeError, ValueError):
        return 5.0


def _sensor_timeout():
    try:
        return float(getattr(settings, 'NODERED_SENSOR_TIMEOUT', 15))
    except (TypeError, ValueError):
        return 15.0


def _headers():
    headers = {'Accept': 'application/json'}

    # Node-RED todavia no implementa un esquema de autenticacion compatible.
    # NODERED_API_TOKEN queda reservado para el futuro; enviarlo ahora no
    # aportaria seguridad y podria romper la integracion. No se envia.
    if getattr(settings, 'NODERED_API_TOKEN', ''):
        logger.debug('NODERED_API_TOKEN configurado pero no enviado (Node-RED sin auth).')

    return headers


def _request(method, path, **kwargs):
    url = f'{_base_url()}{path}'
    kwargs.setdefault('timeout', _timeout())
    kwargs.setdefault('headers', _headers())

    try:
        response = getattr(requests, method)(url, **kwargs)
    except requests.Timeout as exc:
        raise NodeRedTimeout('Node-RED no respondio dentro del tiempo esperado.') from exc
    except requests.ConnectionError as exc:
        raise NodeRedUnavailable('No fue posible conectar con Node-RED.') from exc
    except requests.RequestException as exc:
        raise NodeRedResponseError('Error de comunicacion con Node-RED.') from exc

    return response


def check_health():
    """Consulta /health de Node-RED y devuelve su cuerpo JSON."""
    response = _request('get', HEALTH_PATH)

    if response.status_code != 200:
        raise NodeRedResponseError(
            f'Node-RED respondio con estado HTTP {response.status_code}.'
        )

    try:
        data = response.json()
    except ValueError as exc:
        raise NodeRedResponseError('Node-RED devolvio una respuesta no valida.') from exc

    if not isinstance(data, dict) or data.get('status') != 'ok':
        raise NodeRedResponseError('Node-RED no reporto un estado saludable.')

    return data


def send_command(dispositivo, estado):
    """Envia un comando validado a /control de Node-RED.

    Una respuesta 2xx solo confirma que Node-RED acepto la solicitud y
    solicito la publicacion MQTT; no confirma la ejecucion fisica en el ESP32.
    """
    if dispositivo not in VALID_DEVICES:
        raise ValueError(f'Dispositivo no permitido: {dispositivo!r}.')
    if estado not in VALID_STATES:
        raise ValueError(f'Estado no permitido: {estado!r}.')

    payload = {'dispositivo': dispositivo, 'estado': estado}
    response = _request('post', CONTROL_PATH, json=payload)

    if not 200 <= response.status_code < 300:
        raise NodeRedResponseError(
            f'Node-RED respondio con estado HTTP {response.status_code}.'
        )

    logger.info(
        'Comando enviado a Node-RED: dispositivo=%s estado=%s status=%s',
        dispositivo,
        estado,
        response.status_code,
    )

    return {
        'payload': payload,
        'status_code': response.status_code,
    }


def _response_json(response):
    try:
        data = response.json()
    except ValueError as exc:
        raise NodeRedResponseError(
            'Node-RED devolvio una respuesta no valida.'
        ) from exc

    if not isinstance(data, dict):
        raise NodeRedResponseError('Node-RED devolvio una respuesta no valida.')

    return data


def _raise_for_status(response):
    if response.status_code == 504:
        raise NodeRedTimeout('Node-RED no respondio dentro del tiempo esperado.')
    if response.status_code == 503:
        raise NodeRedUnavailable('Node-RED no esta disponible.')
    if not 200 <= response.status_code < 300:
        raise NodeRedResponseError(
            f'Node-RED respondio con estado HTTP {response.status_code}.'
        )


def activate_motor(duracion=5):
    """Solicita a Node-RED encender la bomba durante ``duracion`` segundos."""
    try:
        duracion = int(duracion)
    except (TypeError, ValueError):
        duracion = 5
    if duracion <= 0 or duracion > 60:
        duracion = 5

    response = _request('post', MOTOR_PATH, json={'duracion': duracion})
    _raise_for_status(response)
    data = _response_json(response)

    logger.info(
        'Motor solicitado a Node-RED: duracion=%ss status=%s',
        duracion,
        response.status_code,
    )

    return {
        'status': 'ok',
        'bomba': data.get('bomba', 'encendida'),
        'duracion': data.get('duracion', duracion),
        'node_red_status': response.status_code,
    }


def read_sensor():
    """Solicita a Node-RED una lectura sincronica del sensor."""
    response = _request(
        'post',
        SENSOR_PATH,
        json={},
        timeout=_sensor_timeout(),
    )
    _raise_for_status(response)
    data = _response_json(response)

    if data.get('status') == 'error':
        error = data.get('error') or 'sensor_error'
        raise NodeRedResponseError(f'Node-RED reporto un error: {error}.')

    if 'humedad' not in data:
        raise NodeRedResponseError('Node-RED no devolvio la humedad del sensor.')

    logger.info('Lectura de sensor recibida desde Node-RED: %s', data.get('humedad'))

    return {
        'status': 'ok',
        'humedad': data.get('humedad'),
        'timestamp': data.get('timestamp'),
        'request_id': data.get('request_id'),
    }
