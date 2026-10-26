from dataclasses import asdict

from django.utils import timezone
from drf_spectacular.utils import extend_schema
from rest_framework import serializers
from rest_framework.response import Response
from rest_framework.views import APIView

from config import composition
from config.api import ListQuery, StrictSerializer, validated
from tapme.businesses.point_scope import request_scope, scoped_query
from tapme.reminders.domain import ReminderConfiguration, ReminderRules, Scenario, ScenarioStep


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
    scenario = serializers.UUIDField(required=False)
    kind = serializers.ChoiceField(choices=["all", "date", "inactive"], default="all")
    state = serializers.ChoiceField(
        choices=["wait", "sent", "skipped", "answered", "ordered"], default="wait"
    )


class ReminderOutput(serializers.Serializer):
    point_id = serializers.UUIDField(allow_null=True)
    point_name = serializers.CharField()
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
    pause_reason = serializers.CharField()
    scenario_id = serializers.UUIDField(allow_null=True)
    scenario_name = serializers.CharField()
    event_date = serializers.DateField(allow_null=True)
    sent_at = serializers.DateTimeField(allow_null=True)
    order_id = serializers.UUIDField(allow_null=True)
    last_order = serializers.JSONField(allow_null=True)
    last_year_hint = serializers.JSONField(allow_null=True)


class ReminderPage(serializers.Serializer):
    count = serializers.IntegerField()
    results = ReminderOutput(many=True)
    stats = serializers.DictField(child=serializers.IntegerField())
    summary = serializers.JSONField()
    scenarios = serializers.JSONField()
    rules = serializers.JSONField()


class ActionInput(StrictSerializer):
    action = serializers.ChoiceField(
        choices=["sent", "skipped", "tomorrow", "answered", "ordered", "undo", "opt_out"]
    )
    order_id = serializers.UUIDField(required=False)


class MessageOutput(serializers.Serializer):
    message = serializers.CharField()
    url = serializers.URLField()


class RulesView(APIView):
    @extend_schema(responses=RulesInput)
    def get(self, request, business_id):
        return Response(asdict(composition.reminders().rules(request_scope(request, business_id))))

    @extend_schema(request=RulesInput, responses=RulesInput)
    def put(self, request, business_id):
        data = validated(RulesInput, request.data)
        data["offsets"] = tuple(data["offsets"])
        if "custom_templates" not in data:
            # Older clients editing reminder rules must not erase saved custom messages.
            data["custom_templates"] = (
                composition.reminders().rules(request_scope(request, business_id)).custom_templates
            )
        return Response(
            asdict(
                composition.reminders().save_rules(
                    request_scope(request, business_id), ReminderRules(**data)
                )
            )
        )


class GeneratedOutput(serializers.Serializer):
    created = serializers.IntegerField()


class ReminderListView(APIView):
    @extend_schema(parameters=[ReminderQuery], responses=ReminderPage)
    def get(self, request, business_id):
        result = composition.reminders().list(
            request_scope(request, business_id),
            now=timezone.now(),
            **validated(ReminderQuery, scoped_query(request)),
        )
        return Response(result)

    @extend_schema(request=None, responses=GeneratedOutput)
    def post(self, request, business_id):
        return Response(
            {
                "created": composition.reminders().generate(
                    request_scope(request, business_id), timezone.now()
                )
            }
        )


class MessageEditInput(StrictSerializer):
    message = serializers.CharField(max_length=2000)


class ReminderMessageView(APIView):
    @extend_schema(responses=MessageOutput)
    def get(self, request, business_id, reminder_id):
        return Response(
            composition.reminders().prepare(
                request_scope(request, business_id), reminder_id, timezone.now()
            )
        )

    @extend_schema(request=MessageEditInput, responses={204: None})
    def patch(self, request, business_id, reminder_id):
        data = validated(MessageEditInput, request.data)
        composition.reminders().edit_message(
            request_scope(request, business_id), reminder_id, data["message"]
        )
        return Response(status=204)


class ReminderOpenView(APIView):
    @extend_schema(request=None, responses=MessageOutput)
    def post(self, request, business_id, reminder_id):
        return Response(
            composition.reminders().open_message(
                request_scope(request, business_id), reminder_id, timezone.now()
            )
        )


class StepInput(StrictSerializer):
    id = serializers.UUIDField()
    offset_days = serializers.IntegerField(min_value=0, max_value=730)
    template = serializers.CharField(max_length=2000)
    enabled = serializers.BooleanField(default=True)


class ScenarioInput(StrictSerializer):
    id = serializers.UUIDField()
    name = serializers.CharField(max_length=100)
    kind = serializers.ChoiceField(
        choices=["before_event", "after_last_order", "after_delivery", "holiday"]
    )
    enabled = serializers.BooleanField()
    event_labels = serializers.ListField(
        child=serializers.CharField(max_length=100), max_length=30, default=list
    )
    holiday_month = serializers.IntegerField(min_value=1, max_value=12, default=3)
    holiday_day = serializers.IntegerField(min_value=1, max_value=31, default=8)
    audience = serializers.ChoiceField(
        choices=["consented_all", "ordered_last_year"], default="consented_all"
    )
    daily_cap = serializers.IntegerField(min_value=1, max_value=500, default=40)
    steps = StepInput(many=True, min_length=1, max_length=15)


class ConfigurationInput(StrictSerializer):
    version = serializers.IntegerField(min_value=1)
    enabled = serializers.BooleanField()
    start_hour = serializers.IntegerField(min_value=0, max_value=23)
    end_hour = serializers.IntegerField(min_value=1, max_value=24)
    min_days_between = serializers.IntegerField(min_value=0, max_value=365)
    scenarios = ScenarioInput(many=True, min_length=1, max_length=30)


class ConfigurationView(APIView):
    @extend_schema(responses=ConfigurationInput)
    def get(self, request, business_id):
        return Response(
            asdict(composition.reminders().configuration(request_scope(request, business_id)))
        )

    @extend_schema(request=ConfigurationInput, responses=ConfigurationInput)
    def put(self, request, business_id):
        data = validated(ConfigurationInput, request.data)
        data["scenarios"] = tuple(
            Scenario(
                **{
                    **s,
                    "event_labels": tuple(s["event_labels"]),
                    "steps": tuple(ScenarioStep(**step) for step in s["steps"]),
                }
            )
            for s in data["scenarios"]
        )
        return Response(
            asdict(
                composition.reminders().save_configuration(
                    request_scope(request, business_id), ReminderConfiguration(**data)
                )
            )
        )


class ReminderActionView(APIView):
    @extend_schema(request=ActionInput, responses={204: None})
    def post(self, request, business_id, reminder_id):
        composition.reminders().act(
            request_scope(request, business_id),
            reminder_id,
            now=timezone.now(),
            **validated(ActionInput, request.data),
        )
        return Response(status=204)
