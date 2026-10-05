from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from config import composition
from config.api import ListQuery, StrictSerializer, validated
from tapme.businesses.application.contracts import Scope


class ProductInput(StrictSerializer):
    name = serializers.CharField(max_length=200)
    price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)


class ProductOutput(ProductInput):
    active = serializers.BooleanField()
    id = serializers.UUIDField()
    version = serializers.IntegerField()


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
            Scope(request.user.id, business_id), **validated(ProductInput, request.data)
        )
        return Response(ProductOutput(product).data, status=201)


class ProductUpdate(ProductInput):
    active = serializers.BooleanField(default=True)
    version = serializers.IntegerField(min_value=1)


class ProductDetailView(APIView):
    @extend_schema(request=ProductUpdate, responses=ProductOutput)
    def put(self, request, business_id, product_id):
        product = composition.catalog().update(
            Scope(request.user.id, business_id),
            product_id,
            **validated(ProductUpdate, request.data),
        )
        return Response(ProductOutput(product).data)
