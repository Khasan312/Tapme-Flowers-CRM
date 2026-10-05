from uuid import UUID

from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from config import composition
from config.api import ListQuery, StrictSerializer, validated
from tapme.businesses.application.contracts import Scope
from tapme.orders.application.services import CreateOrder, ItemInput
from tapme.orders.domain import Fulfillment


class ItemSerializer(StrictSerializer):
    product_id = serializers.UUIDField()
    quantity = serializers.IntegerField(min_value=1, max_value=999)


class OrderInput(StrictSerializer):
    occasion = serializers.CharField(max_length=100, allow_blank=True, default="")
    source = serializers.CharField(max_length=80, allow_blank=True, default="")
    relation = serializers.CharField(max_length=80, allow_blank=True, default="")
    customer_id = serializers.UUIDField()
    items = ItemSerializer(many=True, min_length=1, max_length=50)
    recipient_name = serializers.CharField(max_length=150)
    recipient_phone = serializers.CharField(max_length=40, allow_blank=True, default="")
    fulfillment = serializers.ChoiceField(choices=[f.value for f in Fulfillment])
    delivery_date = serializers.DateField()
    window_start = serializers.TimeField()
    window_end = serializers.TimeField()
    address = serializers.CharField(max_length=500, allow_blank=True, default="")
    notes = serializers.CharField(max_length=2000, allow_blank=True, default="")
    card = serializers.CharField(max_length=1000, allow_blank=True, default="")


class LineOutput(serializers.Serializer):
    product_id = serializers.UUIDField()
    name = serializers.CharField()
    unit_price = serializers.DecimalField(max_digits=12, decimal_places=2)
    quantity = serializers.IntegerField()
    total = serializers.DecimalField(max_digits=12, decimal_places=2)


class OrderOutput(serializers.Serializer):
    occasion = serializers.CharField()
    source = serializers.CharField()
    relation = serializers.CharField()
    id = serializers.UUIDField()
    number = serializers.IntegerField()
    customer_id = serializers.UUIDField()
    customer_name = serializers.CharField()
    customer_phone = serializers.CharField()
    recipient_name = serializers.CharField()
    recipient_phone = serializers.CharField()
    fulfillment = serializers.CharField()
    delivery_date = serializers.DateField()
    window_start = serializers.TimeField()
    window_end = serializers.TimeField()
    address = serializers.CharField()
    notes = serializers.CharField()
    card = serializers.CharField()
    lines = LineOutput(many=True)
    total = serializers.DecimalField(max_digits=12, decimal_places=2)
    status = serializers.CharField()
    created_at = serializers.DateTimeField()
    version = serializers.IntegerField()
    florist_id = serializers.UUIDField(allow_null=True)
    courier_id = serializers.UUIDField(allow_null=True)
    completed_at = serializers.DateTimeField(allow_null=True)
    cancellation_reason = serializers.CharField()
    delivery_issue = serializers.CharField()
    delivery_fee = serializers.DecimalField(max_digits=12, decimal_places=2)
    paid_amount = serializers.DecimalField(max_digits=12, decimal_places=2)


class OrderPage(serializers.Serializer):
    count = serializers.IntegerField()
    results = OrderOutput(many=True)


class OrderQuery(ListQuery):
    day = serializers.DateField(required=False)
    search = serializers.CharField(max_length=150, allow_blank=True, default="")
    status = serializers.ChoiceField(
        choices=["", "new", "work", "ready", "route", "done", "cancelled"], default=""
    )
    customer_id = serializers.UUIDField(required=False)


class OrderListView(APIView):
    @extend_schema(operation_id="orders_list", parameters=[OrderQuery], responses=OrderPage)
    def get(self, request, business_id):
        page = composition.orders().list(
            Scope(request.user.id, business_id), **validated(OrderQuery, request.query_params)
        )
        return Response(OrderPage(page).data)

    @extend_schema(
        request=OrderInput,
        responses={201: OrderOutput},
        parameters=[
            OpenApiParameter("Idempotency-Key", UUID, OpenApiParameter.HEADER, required=True),
        ],
    )
    def post(self, request, business_id):
        try:
            request_key = UUID(request.headers.get("Idempotency-Key", ""))
        except ValueError:
            raise serializers.ValidationError(
                {"Idempotency-Key": "Укажите UUID ключа запроса."}
            ) from None
        values = validated(OrderInput, request.data)
        values["items"] = tuple(ItemInput(**item) for item in values["items"])
        values["fulfillment"] = Fulfillment(values["fulfillment"])
        order = composition.orders().create(
            Scope(request.user.id, business_id), CreateOrder(**values), request_key
        )
        return Response(OrderOutput(order).data, status=201)


class OrderDetailView(APIView):
    @extend_schema(operation_id="orders_retrieve", responses=OrderOutput)
    def get(self, request, business_id, order_id):
        order = composition.orders().get(Scope(request.user.id, business_id), order_id)
        return Response(OrderOutput(order).data)
