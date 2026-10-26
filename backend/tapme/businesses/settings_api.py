from dataclasses import asdict

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from config import composition
from config.api import StrictSerializer, validated
from tapme.businesses.application.contracts import Role, Scope
from tapme.businesses.application.settings import ShopSettings
from tapme.businesses.point_scope import request_scope


class WindowInput(StrictSerializer):
    start = serializers.TimeField(format="%H:%M")
    end = serializers.TimeField(format="%H:%M")
    capacity = serializers.IntegerField(min_value=1, max_value=999, default=6)
    price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0, default="0.00")


class SettingsInput(StrictSerializer):
    version = serializers.IntegerField(min_value=1)
    name = serializers.CharField(max_length=150)
    address = serializers.CharField(max_length=500, allow_blank=True)
    phone = serializers.CharField(max_length=40, allow_blank=True)
    timezone = serializers.CharField(max_length=60)
    windows = WindowInput(many=True, min_length=1, max_length=24)
    city = serializers.CharField(max_length=100, allow_blank=True, default="")
    whatsapp = serializers.CharField(max_length=40, allow_blank=True, default="")
    opening_hours = serializers.CharField(max_length=150, allow_blank=True, default="")
    pickup_unlimited = serializers.BooleanField(default=True)
    enforce_capacity = serializers.BooleanField(default=False)


class StaffOutput(serializers.Serializer):
    point_ids = serializers.ListField(child=serializers.UUIDField())
    id = serializers.UUIDField()
    username = serializers.CharField()
    name = serializers.CharField()
    role = serializers.CharField()
    is_active = serializers.BooleanField()
    phone = serializers.CharField(allow_blank=True)


class StaffInput(StrictSerializer):
    username = serializers.CharField(max_length=150)
    password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)
    name = serializers.CharField(max_length=150)
    role = serializers.ChoiceField(choices=["manager", "florist", "courier"])
    staff_phone = serializers.CharField(max_length=40, allow_blank=True, default="")


class StaffUpdate(StrictSerializer):
    role = serializers.ChoiceField(choices=["manager", "florist", "courier"])
    is_active = serializers.BooleanField()
    staff_phone = serializers.CharField(max_length=40, allow_blank=True, required=False)


class SettingsView(APIView):
    @extend_schema(responses=SettingsInput)
    def get(self, request, business_id):
        scope = request_scope(request, business_id)
        if scope.point_id:
            from tapme.businesses.points_api import service

            data = service().get(scope, scope.point_id)
            return Response({k: data[k] for k in ShopSettings.__dataclass_fields__})
        return Response(asdict(composition.settings().get(scope)))

    @extend_schema(request=SettingsInput, responses=SettingsInput)
    def put(self, request, business_id):
        data = validated(SettingsInput, request.data)
        data["windows"] = [
            {
                "start": window["start"].strftime("%H:%M"),
                "end": window["end"].strftime("%H:%M"),
                "capacity": window["capacity"],
                "price": str(window["price"]),
            }
            for window in data["windows"]
        ]
        result = composition.settings().save(
            Scope(request.user.id, business_id), ShopSettings(**data)
        )
        return Response(asdict(result))


class StaffView(APIView):
    @extend_schema(responses=StaffOutput(many=True))
    def get(self, request, business_id):
        return Response(composition.settings().staff(Scope(request.user.id, business_id)))

    @extend_schema(request=StaffInput, responses={201: StaffOutput})
    def post(self, request, business_id):
        data = validated(StaffInput, request.data)
        data["role"] = Role(data["role"])
        return Response(
            composition.settings().create_staff(Scope(request.user.id, business_id), **data),
            status=201,
        )


class StaffDetailView(APIView):
    @extend_schema(request=None, responses={204: None})
    def delete(self, request, business_id, user_id):
        composition.settings().delete_staff(Scope(request.user.id, business_id), user_id)
        return Response(status=204)

    @extend_schema(request=StaffUpdate, responses={204: None})
    def put(self, request, business_id, user_id):
        data = validated(StaffUpdate, request.data)
        data["role"] = Role(data["role"])
        composition.settings().update_staff(Scope(request.user.id, business_id), user_id, **data)
        return Response(status=204)


class ResetStaffInput(StrictSerializer):
    password = serializers.CharField(max_length=128, trim_whitespace=False, write_only=True)


class ResetStaffView(APIView):
    @extend_schema(request=ResetStaffInput, responses={204: None})
    def post(self, request, business_id, user_id):
        composition.settings().reset_staff(
            Scope(request.user.id, business_id), user_id, **validated(ResetStaffInput, request.data)
        )
        return Response(status=204)
