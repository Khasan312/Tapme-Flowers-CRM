from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from config.api import StrictSerializer, validated
from tapme.businesses.application.contracts import Scope
from tapme.businesses.application.points import PointService
from tapme.businesses.infrastructure.access import DjangoMembershipReader
from tapme.businesses.infrastructure.points import DjangoPointRepository
from tapme.businesses.settings_api import WindowInput


def service():
    return PointService(DjangoMembershipReader(), DjangoPointRepository())


class PointInput(StrictSerializer):
    version = serializers.IntegerField(min_value=1, required=False)
    name = serializers.CharField(max_length=150, required=False)
    short_name = serializers.CharField(max_length=40, required=False)
    address = serializers.CharField(max_length=500, allow_blank=True, required=False)
    phone = serializers.CharField(max_length=40, allow_blank=True, required=False)
    city = serializers.CharField(max_length=100, allow_blank=True, required=False)
    whatsapp = serializers.CharField(max_length=40, allow_blank=True, required=False)
    opening_hours = serializers.CharField(max_length=150, allow_blank=True, required=False)
    pickup_unlimited = serializers.BooleanField(required=False)
    enforce_capacity = serializers.BooleanField(required=False)
    windows = WindowInput(many=True, min_length=1, max_length=24, required=False)
    is_primary = serializers.BooleanField(required=False)
    sort = serializers.IntegerField(min_value=0, required=False)


class PointSummary(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    short_name = serializers.CharField()
    address = serializers.CharField()
    city = serializers.CharField()
    active = serializers.BooleanField()
    is_primary = serializers.BooleanField()
    version = serializers.IntegerField()
    sort = serializers.IntegerField()
    windows = WindowInput(many=True)


class PointOutput(PointSummary):
    phone = serializers.CharField()
    whatsapp = serializers.CharField()
    opening_hours = serializers.CharField()
    timezone = serializers.CharField()
    pickup_unlimited = serializers.BooleanField()
    enforce_capacity = serializers.BooleanField()


def values(request):
    result = validated(PointInput, request.data)
    if "windows" in result:
        result["windows"] = [
            dict(
                start=w["start"].strftime("%H:%M"),
                end=w["end"].strftime("%H:%M"),
                capacity=w["capacity"],
                price=str(w["price"]),
            )
            for w in result["windows"]
        ]
    return result


class PointsView(APIView):
    @extend_schema(responses=PointSummary(many=True))
    def get(self, request, business_id):
        return Response(service().list(Scope(request.user.id, business_id)))

    @extend_schema(request=PointInput, responses={201: PointOutput})
    def post(self, request, business_id):
        data = values(request)
        if not data.get("name") or not data.get("short_name"):
            raise serializers.ValidationError("Укажите название и короткое название точки.")
        return Response(service().save(Scope(request.user.id, business_id), None, data), status=201)


class PointDetailView(APIView):
    @extend_schema(responses=PointOutput)
    def get(self, request, business_id, point_id):
        return Response(service().get(Scope(request.user.id, business_id), point_id))

    @extend_schema(request=PointInput, responses=PointOutput)
    def patch(self, request, business_id, point_id):
        return Response(
            service().save(Scope(request.user.id, business_id), point_id, values(request))
        )


class PointVersionInput(StrictSerializer):
    version = serializers.IntegerField(min_value=1)


class PointArchiveView(APIView):
    @extend_schema(request=PointVersionInput, responses={204: None})
    def post(self, request, business_id, point_id):
        service().archive(
            Scope(request.user.id, business_id),
            point_id,
            **validated(PointVersionInput, request.data),
        )
        return Response(status=204)


class StaffPointsInput(StrictSerializer):
    point_ids = serializers.ListField(child=serializers.UUIDField(), max_length=100)


class StaffPointsView(APIView):
    @extend_schema(request=StaffPointsInput, responses={204: None})
    def put(self, request, business_id, user_id):
        service().staff_points(
            Scope(request.user.id, business_id),
            user_id,
            **validated(StaffPointsInput, request.data),
        )
        return Response(status=204)
