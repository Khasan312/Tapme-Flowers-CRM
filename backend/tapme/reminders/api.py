from dataclasses import asdict

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from config import composition
from config.api import ListQuery, StrictSerializer, validated
from tapme.businesses.application.contracts import Scope
from tapme.reminders.domain import ReminderRules


class CustomTemplateInput(StrictSerializer):
    id = serializers.CharField(max_length=36)
    name = serializers.CharField(max_length=100)
    text = serializers.CharField(max_length=2000)


class RulesInput(StrictSerializer):
    version = serializers.IntegerField(min_value=1)
    enabled = serializers.BooleanField()
    offsets = serializers.ListField(
        child=serializers.IntegerField(min_value=0, max_value=60), min_length=1, max_length=61
    )
    inactive_days = serializers.IntegerField(min_value=30, max_value=730)
    start_hour = serializers.IntegerField(min_value=0, max_value=23)
    end_hour = serializers.IntegerField(min_value=1, max_value=24)
    templates = serializers.DictField(child=serializers.CharField(max_length=2000), default=dict)
    custom_templates = CustomTemplateInput(many=True, max_length=50, required=False)
    template = serializers.CharField(max_length=2000)
    inactive_template = serializers.CharField(
        max_length=2000, default=ReminderRules().inactive_template
    )


class ReminderQuery(ListQuery):
    kind = serializers.ChoiceField(choices=["all", "date", "inactive"], default="all")
    state = serializers.ChoiceField(
        choices=["wait", "sent", "skipped", "answered", "ordered"], default="wait"
    )


class ReminderOutput(serializers.Serializer):
    recovered = serializers.BooleanField()
    kind = serializers.CharField()
    id = serializers.UUIDField()
    customer_id = serializers.UUIDField()
    customer_name = serializers.CharField()
    phone = serializers.CharField()
    event = serializers.CharField()
    person = serializers.CharField()
    due_date = serializers.DateField()
    state = serializers.CharField()
    message = serializers.CharField()
    preview = serializers.CharField()
    paused = serializers.BooleanField()


class ReminderPage(serializers.Serializer):
    count = serializers.IntegerField()
    results = ReminderOutput(many=True)
    stats = serializers.DictField(child=serializers.IntegerField())


class ActionInput(StrictSerializer):
    action = serializers.ChoiceField(choices=["sent", "skipped", "tomorrow", "answered", "ordered"])


class MessageOutput(serializers.Serializer):
    message = serializers.CharField()
    url = serializers.URLField()


class RulesView(APIView):
    @extend_schema(responses=RulesInput)
    def get(self, request, business_id):
        return Response(asdict(composition.reminders().rules(Scope(request.user.id, business_id))))

    @extend_schema(request=RulesInput, responses=RulesInput)
    def put(self, request, business_id):
        data = validated(RulesInput, request.data)
        data["offsets"] = tuple(data["offsets"])
        if "custom_templates" not in data:
            # Older clients editing reminder rules must not erase saved custom messages.
            data["custom_templates"] = (
                composition.reminders().rules(Scope(request.user.id, business_id)).custom_templates
            )
        return Response(
            asdict(
                composition.reminders().save_rules(
                    Scope(request.user.id, business_id), ReminderRules(**data)
                )
            )
        )


class GeneratedOutput(serializers.Serializer):
    created = serializers.IntegerField()


class ReminderListView(APIView):
    @extend_schema(parameters=[ReminderQuery], responses=ReminderPage)
    def get(self, request, business_id):
        result = composition.reminders().list(
            Scope(request.user.id, business_id),
            now=timezone.now(),
            **validated(ReminderQuery, request.query_params),
        )
        return Response(result)

    @extend_schema(request=None, responses=GeneratedOutput)
    def post(self, request, business_id):
        return Response(
            {
                "created": composition.reminders().generate(
                    Scope(request.user.id, business_id), timezone.now()
                )
            }
        )


class ReminderMessageView(APIView):
    @extend_schema(responses=MessageOutput)
    def get(self, request, business_id, reminder_id):
        return Response(
            composition.reminders().prepare(
                Scope(request.user.id, business_id), reminder_id, timezone.now()
            )
        )


class ReminderActionView(APIView):
    @extend_schema(request=ActionInput, responses={204: None})
    def post(self, request, business_id, reminder_id):
        composition.reminders().act(
            Scope(request.user.id, business_id),
            reminder_id,
            now=timezone.now(),
            **validated(ActionInput, request.data),
        )
        return Response(status=204)
