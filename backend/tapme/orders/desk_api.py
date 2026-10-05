from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from config import composition
from config.api import ListQuery, StrictSerializer, validated
from tapme.businesses.application.contracts import Scope
from tapme.orders.api import OrderOutput


class DeskQuery(ListQuery):
    scope = serializers.ChoiceField(
        choices=["today", "tomorrow", "upcoming", "pickup", "unpaid", "all", "date"],
        default="today",
    )
    day = serializers.DateField(required=False)
    search = serializers.CharField(max_length=150, allow_blank=True, default="")
    status = serializers.ChoiceField(
        choices=[
            "",
            "courier",
            "build",
            "delivery",
            "pickup",
            "new",
            "work",
            "ready",
            "route",
            "done",
            "cancelled",
        ],
        default="",
    )


class DeskOutput(serializers.Serializer):
    count = serializers.IntegerField()
    results = OrderOutput(many=True)
    summary = serializers.DictField()
    scopes = serializers.DictField(child=serializers.IntegerField())
    tasks = serializers.ListField(child=serializers.DictField())
    calendar = serializers.ListField(child=serializers.DictField())


class DeskView(APIView):
    @extend_schema(parameters=[DeskQuery], responses=DeskOutput)
    def get(self, request, business_id):
        data = validated(DeskQuery, request.query_params)
        data["day"] = str(data.get("day", ""))
        result = composition.order_desk().read(
            Scope(request.user.id, business_id), now=timezone.now(), **data
        )
        return Response(DeskOutput(result).data)


class NoteInput(StrictSerializer):
    content = serializers.CharField(max_length=500)


class NoteOutput(NoteInput):
    id = serializers.UUIDField()


class NotesView(APIView):
    @extend_schema(responses=NoteOutput(many=True))
    def get(self, request, business_id):
        return Response(composition.order_desk().notes(Scope(request.user.id, business_id)))

    @extend_schema(request=NoteInput, responses={201: NoteOutput})
    def post(self, request, business_id):
        return Response(
            composition.order_desk().add_note(
                Scope(request.user.id, business_id), **validated(NoteInput, request.data)
            ),
            status=201,
        )


class NoteDoneView(APIView):
    @extend_schema(request=None, responses={204: None})
    def post(self, request, business_id, note_id):
        composition.order_desk().complete_note(Scope(request.user.id, business_id), note_id)
        return Response(status=204)
