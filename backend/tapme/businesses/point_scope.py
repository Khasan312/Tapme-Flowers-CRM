"""Translate an explicit HTTP point selection into the application scope."""

from uuid import UUID

from rest_framework.exceptions import ValidationError

from tapme.businesses.application.contracts import Scope


def request_scope(request, business_id):
    value = request.query_params.get("point", request.headers.get("X-Tapme-Point", ""))
    if value in {"", "all"}:
        return Scope(request.user.id, business_id)
    try:
        return Scope(request.user.id, business_id, UUID(value))
    except (ValueError, TypeError):
        raise ValidationError({"point": "Выберите точку из списка."}) from None


def scoped_query(request):
    values = request.query_params.copy()
    values.pop("point", None)
    return values
