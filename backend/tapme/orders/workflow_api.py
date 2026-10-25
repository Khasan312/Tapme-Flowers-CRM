from uuid import UUID

from drf_spectacular.utils import extend_schema, extend_schema_field
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from config import composition
from config.api import ListQuery, StrictSerializer, validated
from tapme.businesses.application.contracts import OFFICE_ROLES, authorize
from tapme.businesses.infrastructure.access import DjangoMembershipReader
from tapme.businesses.point_scope import request_scope, scoped_query
from tapme.catalog.api import order_product_photos
from tapme.orders.api import OrderInput, OrderOutput
from tapme.orders.application.services import CreateOrder, ItemInput
from tapme.orders.domain import Fulfillment


class VersionInput(StrictSerializer):
    version = serializers.IntegerField(min_value=1)


class EditInput(OrderInput):
    version = serializers.IntegerField(min_value=1)


class AssignInput(VersionInput):
    florist_id = serializers.UUIDField(allow_null=True)
    courier_id = serializers.UUIDField(allow_null=True)


class TransitionInput(VersionInput):
    status = serializers.ChoiceField(choices=["new", "work", "ready", "route", "done", "cancelled"])
    reason = serializers.CharField(max_length=1000, allow_blank=True, default="")


class IssueInput(VersionInput):
    detail = serializers.CharField(max_length=1000)


class PaymentInput(StrictSerializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2)
    kind = serializers.ChoiceField(choices=["payment", "refund"])
    method = serializers.ChoiceField(choices=["cash", "transfer", "card"])
    note = serializers.CharField(max_length=1000, allow_blank=True, default="")


class PaymentOutput(PaymentInput):
    id = serializers.UUIDField()
    created_at = serializers.DateTimeField()
    actor_id = serializers.UUIDField()


class TaskOutput(serializers.Serializer):
    point_id = serializers.UUIDField()
    point_name = serializers.SerializerMethodField()

    @extend_schema_field(serializers.CharField())
    def get_point_name(self, order):
        return OrderOutput().get_point_name(order)

    id = serializers.UUIDField()
    number = serializers.IntegerField()
    version = serializers.IntegerField()
    status = serializers.CharField()
    recipient_name = serializers.CharField()
    fulfillment = serializers.CharField()
    delivery_date = serializers.DateField()
    window_start = serializers.TimeField()
    window_end = serializers.TimeField()
    florist_id = serializers.UUIDField(allow_null=True)
    courier_id = serializers.UUIDField(allow_null=True)
    card = serializers.CharField()
    # Task composition deliberately omits prices, buyer contacts and private notes.
    items = serializers.SerializerMethodField()

    @extend_schema_field(serializers.ListField(child=serializers.DictField()))
    def get_items(self, order):
        photos = order_product_photos(order)
        return [
            {
                "name": line.name,
                "quantity": line.quantity,
                "photo_url": photos.get(line.product_id, ""),
            }
            for line in order.lines
        ]


class CourierTaskOutput(TaskOutput):
    delivery_issue = serializers.CharField()
    recipient_phone = serializers.CharField()
    address = serializers.CharField()


class TaskPage(serializers.Serializer):
    count = serializers.IntegerField()
    results = TaskOutput(many=True)


def result_for(request, business_id, order):
    role = DjangoMembershipReader().role_for(request_scope(request, business_id))
    output = (
        OrderOutput
        if role in OFFICE_ROLES
        else CourierTaskOutput
        if role == "courier"
        else TaskOutput
    )
    return output(order).data


class TaskQuery(ListQuery):
    day = serializers.DateField(required=False)


class TaskListView(APIView):
    @extend_schema(parameters=[TaskQuery], responses=TaskPage)
    def get(self, request, business_id):
        page = composition.workflow().tasks(
            request_scope(request, business_id), **validated(TaskQuery, scoped_query(request))
        )
        return Response(
            {
                "count": page.count,
                "results": [result_for(request, business_id, o) for o in page.results],
            }
        )


class EditView(APIView):
    @extend_schema(request=EditInput, responses=OrderOutput)
    def put(self, request, business_id, order_id):
        data = validated(EditInput, request.data)
        version = data.pop("version")
        data["items"] = tuple(ItemInput(**item) for item in data["items"])
        data["fulfillment"] = Fulfillment(data["fulfillment"])
        order = composition.workflow().edit(
            request_scope(request, business_id), order_id, version, CreateOrder(**data)
        )
        return Response(OrderOutput(order).data)


class AssignmentView(APIView):
    @extend_schema(request=AssignInput, responses=OrderOutput)
    def post(self, request, business_id, order_id):
        order = composition.workflow().assign(
            request_scope(request, business_id), order_id, **validated(AssignInput, request.data)
        )
        return Response(OrderOutput(order).data)


class TransitionView(APIView):
    @extend_schema(request=TransitionInput, responses=OrderOutput)
    def post(self, request, business_id, order_id):
        order = composition.workflow().transition(
            request_scope(request, business_id),
            order_id,
            **validated(TransitionInput, request.data),
        )
        return Response(result_for(request, business_id, order))


class DeliveryIssueView(APIView):
    @extend_schema(request=IssueInput, responses=OrderOutput)
    def post(self, request, business_id, order_id):
        order = composition.workflow().issue(
            request_scope(request, business_id), order_id, **validated(IssueInput, request.data)
        )
        return Response(result_for(request, business_id, order))


class PaymentListView(APIView):
    @extend_schema(responses=PaymentOutput(many=True))
    def get(self, request, business_id, order_id):
        composition.orders().get(request_scope(request, business_id), order_id)
        entries = composition.workflow().payments(request_scope(request, business_id), order_id)
        return Response(PaymentOutput(entries, many=True).data)

    @extend_schema(request=PaymentInput, responses={201: PaymentOutput})
    def post(self, request, business_id, order_id):
        try:
            key = UUID(request.headers.get("Idempotency-Key", ""))
        except ValueError:
            raise serializers.ValidationError("Укажите UUID Idempotency-Key.") from None
        entry = composition.workflow().payment(
            request_scope(request, business_id),
            order_id,
            request_key=key,
            **validated(PaymentInput, request.data),
        )
        return Response(PaymentOutput(entry).data, status=201)


class HistoryOutput(serializers.Serializer):
    id = serializers.IntegerField()
    kind = serializers.CharField()
    detail = serializers.CharField()
    created_at = serializers.DateTimeField()
    actor__username = serializers.CharField()


class HistoryView(APIView):
    @extend_schema(responses=HistoryOutput(many=True))
    def get(self, request, business_id, order_id):
        scope = request_scope(request, business_id)
        authorize(DjangoMembershipReader(), scope, OFFICE_ROLES)
        composition.orders().get(scope, order_id)
        return Response(composition.workflow().history(scope, order_id))


class ResolveDeliveryIssueView(APIView):
    @extend_schema(request=VersionInput, responses=OrderOutput)
    def post(self, request, business_id, order_id):
        order = composition.workflow().resolve_issue(
            request_scope(request, business_id), order_id, **validated(VersionInput, request.data)
        )
        return Response(OrderOutput(order).data)
