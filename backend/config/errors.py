from django.http import JsonResponse
from rest_framework.response import Response
from rest_framework.views import exception_handler as drf_exception_handler

from tapme.shared.domain import Conflict, Forbidden, InvalidInput, NotFound


def exception_handler(exc, context):
    for kind, status in ((InvalidInput, 400), (Forbidden, 403), (NotFound, 404), (Conflict, 409)):
        if isinstance(exc, kind):
            return Response({"detail": str(exc)}, status=status)
    return drf_exception_handler(exc, context)


def csrf_failure(request, reason=""):
    return JsonResponse(
        {"detail": "Защитный токен истёк. Обновите страницу и повторите действие."}, status=403
    )
