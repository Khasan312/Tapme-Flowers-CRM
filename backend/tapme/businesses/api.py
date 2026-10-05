from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from tapme.businesses.models import Membership


class BusinessOutput(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    currency = serializers.CharField()
    timezone = serializers.CharField()
    role = serializers.CharField()


class BusinessListView(APIView):
    @extend_schema(responses=BusinessOutput(many=True))
    def get(self, request):
        memberships = (
            Membership.objects.filter(user=request.user, is_active=True)
            .select_related("business")
            .order_by("business__name", "business_id")
        )
        return Response(
            [
                {
                    "id": str(m.business_id),
                    "name": m.business.name,
                    "currency": m.business.currency,
                    "timezone": m.business.timezone,
                    "role": m.role,
                }
                for m in memberships
            ]
        )
