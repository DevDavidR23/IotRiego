import json

from django.http import JsonResponse
from django.views.decorators.http import require_http_methods

from . import services

ALLOWED_FIELDS = frozenset({'dispositivo', 'estado'})


def _error(code, message, status):
    return JsonResponse({'error': message, 'code': code}, status=status)


def _can_control(user):
    return bool(
        user
        and user.is_authenticated
        and user.is_active
        and user.is_staff
    )


def _can_check_health(user):
    return bool(user and user.is_authenticated and user.is_active)


def _json_body(request):
    try:
        data = json.loads(request.body or b'{}')
    except (json.JSONDecodeError, UnicodeDecodeError):
        raise ValueError('El cuerpo de la peticion no es JSON valido.')
    if not isinstance(data, dict):
        raise ValueError('El cuerpo de la peticion debe ser un objeto JSON.')
    return data


def _node_red_error_response(exc):
    if isinstance(exc, services.NodeRedTimeout):
        return _error('node_red_timeout', str(exc), 504)
    if isinstance(exc, services.NodeRedUnavailable):
        return _error('node_red_unavailable', str(exc), 503)
    if isinstance(exc, services.NodeRedNotConfigured):
        return _error('node_red_not_configured', str(exc), 500)
    return _error('node_red_error', str(exc), 502)


@require_http_methods(['POST'])
def control_device(request):
    if not _can_control(request.user):
        return _error(
            'forbidden',
            'Se requieren permisos para controlar los dispositivos.',
            403,
        )

    try:
        data = _json_body(request)
    except ValueError as exc:
        return _error('invalid_json', str(exc), 400)

    unknown_fields = sorted(set(data) - ALLOWED_FIELDS)
    if unknown_fields:
        return _error(
            'invalid_fields',
            f'Campos no permitidos: {", ".join(unknown_fields)}.',
            400,
        )

    missing_fields = sorted(ALLOWED_FIELDS - set(data))
    if missing_fields:
        return _error(
            'missing_fields',
            f'Faltan campos obligatorios: {", ".join(missing_fields)}.',
            400,
        )

    dispositivo = data['dispositivo']
    estado = data['estado']

    if not isinstance(dispositivo, str) or dispositivo not in services.VALID_DEVICES:
        return _error(
            'invalid_device',
            'El campo dispositivo debe ser "bomba" o "sensor".',
            400,
        )

    if not isinstance(estado, str) or estado not in services.VALID_STATES:
        return _error(
            'invalid_state',
            'El campo estado debe ser "ON" o "OFF".',
            400,
        )

    try:
        result = services.send_command(dispositivo, estado)
    except services.NodeRedError as exc:
        return _node_red_error_response(exc)

    return JsonResponse(
        {
            'status': 'accepted',
            'dispositivo': dispositivo,
            'estado': estado,
            'node_red_status': result['status_code'],
            'detail': (
                'Node-RED acepto la solicitud y solicito la publicacion MQTT. '
                'Esto no confirma la ejecucion fisica en el dispositivo.'
            ),
        },
        status=202,
    )


@require_http_methods(['GET'])
def control_health(request):
    if not _can_check_health(request.user):
        return _error(
            'forbidden',
            'Se requiere autenticacion para consultar Node-RED.',
            403,
        )

    try:
        data = services.check_health()
    except services.NodeRedError as exc:
        return _node_red_error_response(exc)

    return JsonResponse(
        {
            'status': 'ok',
            'node_red': data,
            'detail': (
                'Node-RED esta disponible. Esto no indica el estado fisico '
                'de la bomba ni del sensor.'
            ),
        }
    )
