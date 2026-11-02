import json

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.utils.dateparse import parse_date
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import PromedioDiario


def _serialize(registro):
    return {
        'id': registro.id,
        'humedad_promedio': registro.humedad_promedio,
        'fecha': str(registro.fecha),
    }


def _json_body(request):
    try:
        data = json.loads(request.body or b'{}')
    except json.JSONDecodeError:
        raise ValidationError('El cuerpo de la peticion no es JSON valido.')
    if not isinstance(data, dict):
        raise ValidationError('El cuerpo de la peticion debe ser un objeto JSON.')
    return data


def _error(message, status=400):
    return JsonResponse({'error': message}, status=status)


def _parse_humedad(value):
    try:
        return float(value)
    except (TypeError, ValueError):
        raise ValidationError('El campo humedad_promedio debe ser un valor numerico.')


def _parse_fecha(value):
    try:
        fecha = parse_date(str(value))
    except (TypeError, ValueError):
        fecha = None
    if fecha is None:
        raise ValidationError('El campo fecha debe tener formato YYYY-MM-DD.')
    return fecha


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def promedio_diario_list(request):
    if request.method == 'GET':
        registros = PromedioDiario.objects.all()
        return JsonResponse([_serialize(r) for r in registros], safe=False)

    try:
        data = _json_body(request)
        faltantes = [c for c in ('humedad_promedio', 'fecha') if c not in data]
        if faltantes:
            raise ValidationError(f'Faltan campos obligatorios: {", ".join(faltantes)}.')

        registro = PromedioDiario(
            humedad_promedio=_parse_humedad(data['humedad_promedio']),
            fecha=_parse_fecha(data['fecha']),
        )
        registro.full_clean()
        registro.save()
    except ValidationError as exc:
        return _error(exc.messages[0] if hasattr(exc, 'messages') else str(exc))

    return JsonResponse(_serialize(registro), status=201)


@csrf_exempt
@require_http_methods(['GET', 'PUT', 'PATCH', 'DELETE'])
def promedio_diario_detail(request, pk):
    try:
        registro = PromedioDiario.objects.get(pk=pk)
    except PromedioDiario.DoesNotExist:
        return _error('Registro no encontrado.', status=404)

    if request.method == 'GET':
        return JsonResponse(_serialize(registro))

    if request.method == 'DELETE':
        registro.delete()
        return JsonResponse({}, status=204)

    try:
        data = _json_body(request)
        if 'humedad_promedio' in data:
            registro.humedad_promedio = _parse_humedad(data['humedad_promedio'])
        if 'fecha' in data:
            registro.fecha = _parse_fecha(data['fecha'])
        if 'humedad_promedio' not in data and 'fecha' not in data:
            raise ValidationError('Debes enviar humedad_promedio y/o fecha.')

        registro.full_clean()
        registro.save()
    except ValidationError as exc:
        return _error(exc.messages[0] if hasattr(exc, 'messages') else str(exc))

    return JsonResponse(_serialize(registro))
