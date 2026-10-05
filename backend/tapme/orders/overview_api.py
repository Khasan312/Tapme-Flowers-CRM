from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from config import composition
from config.api import StrictSerializer, validated
from tapme.businesses.application.contracts import Scope


class OverviewQuery(StrictSerializer):
    day = serializers.DateField(required=False)


class OverviewOutput(serializers.Serializer):
    deliveries = serializers.IntegerField()
    reminders = serializers.IntegerField()
    deliveries_completed = serializers.IntegerField()
    deliveries_on_time = serializers.IntegerField()
    orders = serializers.IntegerField()
    completed = serializers.IntegerField()
    in_progress = serializers.IntegerField()
    total = serializers.DecimalField(max_digits=18, decimal_places=2)
    payments = serializers.DecimalField(max_digits=18, decimal_places=2)
    refunds = serializers.DecimalField(max_digits=18, decimal_places=2)
    complaints = serializers.IntegerField()


class OverviewView(APIView):
    @extend_schema(parameters=[OverviewQuery], responses=OverviewOutput)
    def get(self, request, business_id):
        day = validated(OverviewQuery, request.query_params).get("day")
        result = composition.overview().get(Scope(request.user.id, business_id), day)
        return Response(OverviewOutput(result).data)
