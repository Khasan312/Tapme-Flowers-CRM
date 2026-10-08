from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from config import composition
from config.api import StrictSerializer, validated
from tapme.businesses.application.contracts import OFFICE_ROLES, Scope, authorize
from tapme.businesses.infrastructure.access import DjangoMembershipReader
from tapme.customers.infrastructure.files import export_customers, read_customers


class ImportInput(StrictSerializer):
    file = serializers.FileField()
    commit = serializers.BooleanField(default=False)
    selected_rows = serializers.JSONField(required=False)

    def validate_selected_rows(self, value):
        if (
            not isinstance(value, list)
            or len(value) > 1000
            or any(type(row) is not int or row < 2 for row in value)
            or len(set(value)) != len(value)
        ):
            raise serializers.ValidationError("Выберите строки из предпросмотра файла.")
        return value


class ImportOutput(serializers.Serializer):
    count = serializers.IntegerField()
    created = serializers.IntegerField()
    results = serializers.ListField(child=serializers.DictField())


class ImportView(APIView):
    parser_classes = [MultiPartParser]

    @extend_schema(request=ImportInput, responses=ImportOutput)
    def post(self, request, business_id):
        scope = Scope(request.user.id, business_id)
        authorize(DjangoMembershipReader(), scope, OFFICE_ROLES)
        data = validated(ImportInput, request.data)
        rows = read_customers(data["file"])
        return Response(
            composition.transfers().import_rows(
                scope, rows, data["commit"], data.get("selected_rows")
            )
        )


class ExportQuery(StrictSerializer):
    kind = serializers.ChoiceField(choices=["csv", "xlsx"], default="xlsx")


class ExportView(APIView):
    @extend_schema(parameters=[ExportQuery], responses={(200, "application/octet-stream"): bytes})
    def get(self, request, business_id):
        kind = validated(ExportQuery, request.query_params)["kind"]
        content, mime = export_customers(
            composition.transfers().export_rows(Scope(request.user.id, business_id)), kind
        )
        response = HttpResponse(content, content_type=mime)
        response["Content-Disposition"] = f'attachment; filename="tapme-customers.{kind}"'
        response["Cache-Control"] = "private, no-store"
        return response
