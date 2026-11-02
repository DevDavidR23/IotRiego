import json

from django.core.exceptions import ValidationError
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_http_methods

from .models import Humedad


def _serialize(registro):
    return {
        'id': registro.id,
        'humedad': registro.humedad,
        'timestamp': registro.timestamp.isoformat(),
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


@csrf_exempt
@require_http_methods(['GET', 'POST'])
def humedad_list(request):
    if request.method == 'GET':
        registros = Humedad.objects.all()
        return JsonResponse([_serialize(r) for r in registros], safe=False)

    try:
        data = _json_body(request)
        if 'humedad' not in data:
            raise ValidationError('El campo humedad es obligatorio.')

        registro = Humedad(humedad=data['humedad'])
        registro.full_clean()
        registro.save()
    except ValidationError as exc:
        return _error(exc.messages[0] if hasattr(exc, 'messages') else str(exc))
    except (TypeError, ValueError):
        return _error('El campo humedad debe ser un valor numerico.')

    return JsonResponse(_serialize(registro), status=201)


@csrf_exempt
@require_http_methods(['GET', 'PUT', 'PATCH', 'DELETE'])
def humedad_detail(request, pk):
    try:
        registro = Humedad.objects.get(pk=pk)
    except Humedad.DoesNotExist:
        return _error('Registro no encontrado.', status=404)

    if request.method == 'GET':
        return JsonResponse(_serialize(registro))

    if request.method == 'DELETE':
        registro.delete()
        return JsonResponse({}, status=204)

    try:
        data = _json_body(request)
        if 'humedad' not in data:
            raise ValidationError('El campo humedad es obligatorio.')

        registro.humedad = data['humedad']
        registro.full_clean()
        registro.save()
    except ValidationError as exc:
        return _error(exc.messages[0] if hasattr(exc, 'messages') else str(exc))
    except (TypeError, ValueError):
        return _error('El campo humedad debe ser un valor numerico.')

    return JsonResponse(_serialize(registro))
