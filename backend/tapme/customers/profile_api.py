from uuid import uuid4

from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from config import composition
from config.api import StrictSerializer, validated
from tapme.businesses.application.contracts import Scope
from tapme.customers.api import CustomerInput
from tapme.customers.domain import Customer, ImportantDate, Recipient


class RecipientInput(StrictSerializer):
    id = serializers.UUIDField(default=uuid4)
    name = serializers.CharField(max_length=150)
    relation = serializers.CharField(max_length=80, allow_blank=True, default="")
    phone = serializers.CharField(max_length=40, allow_blank=True, default="")
    address = serializers.CharField(max_length=500, allow_blank=True, default="")
    notes = serializers.CharField(max_length=2000, allow_blank=True, default="")


class DateInput(StrictSerializer):
    id = serializers.UUIDField(default=uuid4)
    label = serializers.CharField(max_length=150)
    person = serializers.CharField(max_length=150)
    month = serializers.IntegerField(min_value=1, max_value=12)
    day = serializers.IntegerField(min_value=1, max_value=31)


class ProfileInput(CustomerInput):
    additional_phones = serializers.ListField(
        child=serializers.CharField(max_length=40, allow_blank=True), max_length=9, required=False
    )
    code = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    version = serializers.IntegerField(min_value=1)
    recipients = RecipientInput(many=True, max_length=50)
    dates = DateInput(many=True, max_length=50)


class ProfileOutput(ProfileInput):
    code = serializers.IntegerField(read_only=True)
    created_at = serializers.DateTimeField(read_only=True)
    id = serializers.UUIDField()


class CustomerDetailView(APIView):
    @extend_schema(responses=ProfileOutput)
    def get(self, request, business_id, customer_id):
        return Response(
            ProfileOutput(
                composition.profiles().get(Scope(request.user.id, business_id), customer_id)
            ).data
        )

    @extend_schema(request=ProfileInput, responses=ProfileOutput)
    def put(self, request, business_id, customer_id):
        data = validated(ProfileInput, request.data)
        if "additional_phones" not in data:
            current = composition.profiles().get(Scope(request.user.id, business_id), customer_id)
            data["additional_phones"] = current["additional_phones"]
        version = data.pop("version")
        recipients = tuple(Recipient(**r) for r in data.pop("recipients"))
        dates = tuple(ImportantDate(**d) for d in data.pop("dates"))
        customer = Customer(customer_id, business_id, **data)
        return Response(
            ProfileOutput(
                composition.profiles().save(
                    Scope(request.user.id, business_id), customer, version, recipients, dates
                )
            ).data
        )


class ActivityOutput(serializers.Serializer):
    order_count = serializers.IntegerField()
    total = serializers.CharField()
    last_order = serializers.DateField(allow_null=True)
    orders = serializers.ListField(child=serializers.DictField())
    feedback = serializers.ListField(child=serializers.DictField())
    reminders = serializers.ListField(child=serializers.DictField())


class ActivityView(APIView):
    @extend_schema(responses=ActivityOutput)
    def get(self, request, business_id, customer_id):
        return Response(
            composition.customer_activity().get(Scope(request.user.id, business_id), customer_id)
        )
