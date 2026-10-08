from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from config import composition
from config.api import ListQuery, StrictSerializer, validated
from tapme.businesses.application.contracts import Scope


class CustomerInput(StrictSerializer):
    name = serializers.CharField(max_length=150)
    phone = serializers.CharField(max_length=40)
    additional_phones = serializers.ListField(
        child=serializers.CharField(max_length=40, allow_blank=True), max_length=9, default=list
    )
    notes = serializers.CharField(max_length=2000, allow_blank=True, default="")
    consent = serializers.BooleanField(default=False)
    source = serializers.CharField(max_length=80, allow_blank=True, default="")
    tags = serializers.ListField(
        child=serializers.CharField(max_length=40), max_length=10, default=list
    )


class CustomerOutput(CustomerInput):
    id = serializers.UUIDField()


class CustomerPage(serializers.Serializer):
    count = serializers.IntegerField()
    results = CustomerOutput(many=True)


class CustomerQuery(ListQuery):
    search = serializers.CharField(max_length=150, allow_blank=True, default="")


class CustomerListView(APIView):
    @extend_schema(
        operation_id="customers_list", parameters=[CustomerQuery], responses=CustomerPage
    )
    def get(self, request, business_id):
        page = composition.customers().list(
            Scope(request.user.id, business_id), **validated(CustomerQuery, request.query_params)
        )
        return Response(CustomerPage(page).data)

    @extend_schema(request=CustomerInput, responses={201: CustomerOutput})
    def post(self, request, business_id):
        customer = composition.customers().create(
            Scope(request.user.id, business_id), **validated(CustomerInput, request.data)
        )
        return Response(CustomerOutput(customer).data, status=201)
