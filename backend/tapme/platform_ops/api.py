from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView

from config.api import StrictSerializer, validated
from tapme.accounts.permissions import PasswordChanged, PlatformAdmin
from tapme.platform_ops import services
from tapme.platform_ops.models import PlatformEvent


class OwnerOutput(serializers.Serializer):
    id = serializers.UUIDField()
    username = serializers.CharField()
    name = serializers.CharField()
    is_active = serializers.BooleanField()
    last_login = serializers.DateTimeField(allow_null=True)
    must_change_password = serializers.BooleanField()


class CompanyOutput(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    currency = serializers.CharField()
    timezone = serializers.CharField()
    point_count = serializers.IntegerField()
    member_count = serializers.IntegerField()
    owners = OwnerOutput(many=True)


class ProvisionInput(StrictSerializer):
    name = serializers.CharField(max_length=150)
    owner_name = serializers.CharField(max_length=150)
    owner_username = serializers.RegexField(r"^[a-zA-Z0-9][a-zA-Z0-9._@+-]*$", max_length=150)


class CredentialsOutput(serializers.Serializer):
    username = serializers.CharField()
    temporary_password = serializers.CharField()


class ProvisionOutput(serializers.Serializer):
    business = CompanyOutput()
    credentials = CredentialsOutput()


class PlatformView(APIView):
    permission_classes = [IsAuthenticated, PasswordChanged, PlatformAdmin]

    def finalize_response(self, request, response, *args, **kwargs):
        response = super().finalize_response(request, response, *args, **kwargs)
        response["Cache-Control"] = "no-store"
        return response


class CompanyListView(PlatformView):
    @extend_schema(responses=CompanyOutput(many=True))
    def get(self, request):
        return Response(
            CompanyOutput([services.company_data(b) for b in services.companies()], many=True).data
        )

    @extend_schema(request=ProvisionInput, responses={201: ProvisionOutput})
    def post(self, request):
        data = validated(ProvisionInput, request.data)
        return Response(services.provision_company(request.user, **data), status=201)


class OwnerResetView(PlatformView):
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "login"

    @extend_schema(request=None, responses=CredentialsOutput)
    def post(self, request, business_id, owner_id):
        return Response(services.reset_owner_password(request.user, business_id, owner_id))


class EventOutput(serializers.Serializer):
    id = serializers.IntegerField()
    action = serializers.CharField()
    created_at = serializers.DateTimeField()
    actor = serializers.CharField()
    business = serializers.CharField()
    owner = serializers.CharField()


class EventListView(PlatformView):
    @extend_schema(responses=EventOutput(many=True))
    def get(self, request):
        events = PlatformEvent.objects.select_related("actor", "business", "owner")[:100]
        return Response(
            [
                {
                    "id": e.id,
                    "action": e.action,
                    "created_at": e.created_at,
                    "actor": e.actor.username,
                    "business": e.business.name,
                    "owner": e.owner.username,
                }
                for e in events
            ]
        )
