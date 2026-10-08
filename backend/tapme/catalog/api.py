from django.http import HttpResponse
from drf_spectacular.utils import extend_schema, extend_schema_field
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from config import composition
from config.api import ListQuery, StrictSerializer, validated
from tapme.businesses.application.contracts import Scope


def photo_url(business_id, product_id, version):
    return f"/api/v1/businesses/{business_id}/products/{product_id}/photo/?v={version}"


def order_product_photos(order):
    return {
        product_id: photo_url(order.business_id, product_id, version)
        for product_id, version in composition.product_photos()
        .photo_versions(order.business_id, tuple(line.product_id for line in order.lines))
        .items()
    }


def product_values(serializer, data):
    values = validated(serializer, data)
    upload = values.pop("photo", None)
    if upload is not None:
        if upload.size > 10 * 1024 * 1024:
            raise serializers.ValidationError("Фотография должна занимать не более 10 МБ.")
        values["photo"] = upload.read()
    return values


class ProductInput(StrictSerializer):
    name = serializers.CharField(max_length=200)
    price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    photo = serializers.FileField(required=False, write_only=True)


class ProductOutput(ProductInput):
    active = serializers.BooleanField()
    id = serializers.UUIDField()
    version = serializers.IntegerField()
    photo_url = serializers.SerializerMethodField()

    @extend_schema_field(serializers.CharField(allow_blank=True))
    def get_photo_url(self, product):
        return (
            photo_url(product.business_id, product.id, product.version) if product.photo_key else ""
        )


class ProductPage(serializers.Serializer):
    count = serializers.IntegerField()
    results = ProductOutput(many=True)


class ProductQuery(ListQuery):
    include_hidden = serializers.BooleanField(default=False)


class ProductListView(APIView):
    @extend_schema(parameters=[ProductQuery], responses=ProductPage)
    def get(self, request, business_id):
        page = composition.catalog().list(
            Scope(request.user.id, business_id), **validated(ProductQuery, request.query_params)
        )
        return Response(ProductPage(page).data)

    @extend_schema(request=ProductInput, responses={201: ProductOutput})
    def post(self, request, business_id):
        product = composition.catalog().create(
            Scope(request.user.id, business_id), **product_values(ProductInput, request.data)
        )
        return Response(ProductOutput(product).data, status=201)


class ProductUpdate(ProductInput):
    active = serializers.BooleanField(default=True)
    version = serializers.IntegerField(min_value=1)
    remove_photo = serializers.BooleanField(default=False)


class ProductDetailView(APIView):
    @extend_schema(request=ProductUpdate, responses=ProductOutput)
    def put(self, request, business_id, product_id):
        product = composition.catalog().update(
            Scope(request.user.id, business_id),
            product_id,
            **product_values(ProductUpdate, request.data),
        )
        return Response(ProductOutput(product).data)


class ProductPhotoView(APIView):
    @extend_schema(responses={(200, "image/jpeg"): bytes})
    def get(self, request, business_id, product_id):
        content = composition.catalog().photo(Scope(request.user.id, business_id), product_id)
        response = HttpResponse(content, content_type="image/jpeg")
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response
