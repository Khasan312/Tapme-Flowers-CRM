from django.utils.decorators import method_decorator
from django.views.decorators.csrf import csrf_protect
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from config import composition
from config.api import StrictSerializer, validated
from config.throttling import ClientRateThrottle
from tapme.businesses.point_scope import request_scope


class ShareInput(StrictSerializer):
    revoke = serializers.BooleanField(default=False)


class ShareOutput(serializers.Serializer):
    token = serializers.CharField()


class PublicOutput(serializers.Serializer):
    number = serializers.IntegerField()
    status = serializers.CharField()
    fulfillment = serializers.CharField()
    delivery_date = serializers.DateField()
    window_start = serializers.TimeField()
    window_end = serializers.TimeField()
    shop_name = serializers.CharField()
    shop_phone = serializers.CharField()
    can_review = serializers.BooleanField()


class ReviewInput(StrictSerializer):
    message = serializers.CharField(max_length=2000, allow_blank=True, default="")
    rating = serializers.IntegerField(min_value=1, max_value=5)


class ShareView(APIView):
    @extend_schema(request=ShareInput, responses=ShareOutput)
    def post(self, request, business_id, order_id):
        token = composition.public_orders().issue(
            request_scope(request, business_id), order_id, **validated(ShareInput, request.data)
        )
        return Response({"token": token})


@method_decorator(csrf_protect, name="dispatch")
class PublicView(APIView):
    permission_classes = [AllowAny]
    authentication_classes = []
    throttle_classes = [ClientRateThrottle]
    throttle_scope = "public"

    @extend_schema(responses=PublicOutput)
    def get(self, request, token):
        response = Response(composition.public_orders().get(token))
        response["Cache-Control"] = "no-store"
        response["Referrer-Policy"] = "no-referrer"
        return response

    @extend_schema(request=ReviewInput, responses={201: None})
    def post(self, request, token):
        composition.public_orders().feedback(token, **validated(ReviewInput, request.data))
        return Response(status=201)
