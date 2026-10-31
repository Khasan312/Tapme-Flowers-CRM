from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from config import composition
from config.api import StrictSerializer, validated
from tapme.businesses.point_scope import request_scope


class FeedbackInput(StrictSerializer):
    kind = serializers.ChoiceField(choices=["review", "complaint"])
    message = serializers.CharField(max_length=2000)
    rating = serializers.IntegerField(min_value=1, max_value=5, allow_null=True, default=None)


class FeedbackOutput(FeedbackInput):
    id = serializers.UUIDField()
    status = serializers.CharField()
    outcome = serializers.CharField()
    created_at = serializers.DateTimeField()


class ResolveInput(StrictSerializer):
    outcome = serializers.CharField(max_length=2000)


class FeedbackView(APIView):
    @extend_schema(responses=FeedbackOutput(many=True))
    def get(self, request, business_id, order_id):
        composition.orders().get(request_scope(request, business_id), order_id)
        rows = composition.feedback().list(request_scope(request, business_id), order_id)
        return Response(FeedbackOutput(rows, many=True).data)

    @extend_schema(request=FeedbackInput, responses={201: FeedbackOutput})
    def post(self, request, business_id, order_id):
        composition.orders().get(request_scope(request, business_id), order_id)
        row = composition.feedback().create(
            request_scope(request, business_id), order_id, **validated(FeedbackInput, request.data)
        )
        return Response(FeedbackOutput(row).data, status=201)


class ResolveView(APIView):
    @extend_schema(request=ResolveInput, responses={204: None})
    def post(self, request, business_id, feedback_id):
        composition.feedback().resolve(
            request_scope(request, business_id),
            feedback_id,
            **validated(ResolveInput, request.data),
        )
        return Response(status=204)
