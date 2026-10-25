from django.http import HttpResponse
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework.views import APIView

from config import composition
from config.api import StrictSerializer, validated
from tapme.businesses.point_scope import request_scope


class PhotoInput(StrictSerializer):
    kind = serializers.ChoiceField(choices=["bouquet", "delivery"])
    file = serializers.FileField()


class PhotoOutput(serializers.Serializer):
    id = serializers.UUIDField()
    kind = serializers.CharField()
    created_at = serializers.DateTimeField()
    can_delete = serializers.BooleanField()


class PhotoListView(APIView):
    parser_classes = [MultiPartParser]

    @extend_schema(responses=PhotoOutput(many=True))
    def get(self, request, business_id, order_id):
        return Response(
            PhotoOutput(
                composition.photos().list(request_scope(request, business_id), order_id), many=True
            ).data
        )

    @extend_schema(request=PhotoInput, responses={201: PhotoOutput})
    def post(self, request, business_id, order_id):
        data = validated(PhotoInput, request.data)
        if data["file"].size > 10 * 1024 * 1024:
            raise serializers.ValidationError("Фотография должна занимать не более 10 МБ.")
        photo = composition.photos().upload(
            request_scope(request, business_id), order_id, data["kind"], data["file"].read()
        )
        return Response(PhotoOutput(photo).data, status=201)


class PhotoFileView(APIView):
    @extend_schema(responses={204: None})
    def delete(self, request, business_id, order_id, photo_id):
        composition.photos().delete(request_scope(request, business_id), order_id, photo_id)
        return Response(status=204)

    @extend_schema(responses={(200, "image/jpeg"): bytes})
    def get(self, request, business_id, order_id, photo_id):
        content = composition.photos().read(request_scope(request, business_id), order_id, photo_id)
        response = HttpResponse(content, content_type="image/jpeg")
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response
