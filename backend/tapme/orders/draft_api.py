from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from config import composition
from config.api import validated
from tapme.businesses.point_scope import request_scope
from tapme.orders.api import OrderOutput
from tapme.orders.workflow_api import VersionInput


class DraftVersion(VersionInput):
    draft_id = serializers.UUIDField()


class DraftInput(DraftVersion):
    fields = serializers.DictField()


class ConvertInput(DraftVersion):
    payment_due_at = serializers.DateTimeField(required=False, allow_null=True)
    without_prepayment = serializers.BooleanField(default=False)
    reason = serializers.CharField(max_length=1000, allow_blank=True, default="")


class DraftOutput(serializers.Serializer):
    draft = serializers.DictField(allow_null=True)


class DraftView(APIView):
    @extend_schema(request=DraftVersion, responses=DraftOutput)
    def delete(self, request, business_id, chat_id):
        return Response(
            composition.drafts().abandon(
                request_scope(request, business_id),
                chat_id,
                **validated(DraftVersion, request.data),
            )
        )

    @extend_schema(responses=DraftOutput)
    def get(self, request, business_id, chat_id):
        return Response(composition.drafts().read(request_scope(request, business_id), chat_id))

    @extend_schema(request=None, responses=DraftOutput)
    def post(self, request, business_id, chat_id):
        return Response(composition.drafts().start(request_scope(request, business_id), chat_id))

    @extend_schema(request=DraftInput, responses=DraftOutput)
    def put(self, request, business_id, chat_id):
        return Response(
            composition.drafts().save(
                request_scope(request, business_id), chat_id, **validated(DraftInput, request.data)
            )
        )


class DraftRestoreView(APIView):
    @extend_schema(request=DraftVersion, responses=DraftOutput)
    def post(self, request, business_id, chat_id):
        return Response(
            composition.drafts().restore(
                request_scope(request, business_id),
                chat_id,
                **validated(DraftVersion, request.data),
            )
        )


class DraftConvertView(APIView):
    @extend_schema(request=ConvertInput, responses=OrderOutput)
    def post(self, request, business_id, chat_id):
        order = composition.drafts().convert(
            request_scope(request, business_id), chat_id, **validated(ConvertInput, request.data)
        )
        return Response(OrderOutput(order).data)


class ExtendPaymentView(APIView):
    @extend_schema(request=VersionInput, responses=OrderOutput)
    def post(self, request, business_id, order_id):
        order = composition.drafts().extend(
            request_scope(request, business_id), order_id, **validated(VersionInput, request.data)
        )
        return Response(OrderOutput(order).data)
