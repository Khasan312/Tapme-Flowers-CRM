from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from config import composition
from config.api import validated
from tapme.businesses.point_scope import request_scope, scoped_query
from tapme.customers.api import CustomerQuery


class DirectoryQuery(CustomerQuery):
    group = serializers.ChoiceField(
        choices=["all", "vip", "corp", "vip_corp", "new", "lapsed", "whatsapp"], default="all"
    )


class DirectoryOutput(serializers.Serializer):
    count = serializers.IntegerField()
    total_count = serializers.IntegerField()
    consent_count = serializers.IntegerField()
    results = serializers.ListField(child=serializers.DictField())


class DirectoryView(APIView):
    @extend_schema(parameters=[DirectoryQuery], responses=DirectoryOutput)
    def get(self, request, business_id):
        return Response(
            composition.customer_directory().list(
                request_scope(request, business_id),
                now=timezone.now(),
                **validated(DirectoryQuery, scoped_query(request)),
            )
        )
