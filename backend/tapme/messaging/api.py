import hmac
import json
from decimal import Decimal

from django.conf import settings
from django.http import HttpResponse, JsonResponse
from django.utils.http import content_disposition_header
from django.views.decorators.csrf import csrf_exempt
from drf_spectacular.utils import (
    OpenApiParameter,
    OpenApiTypes,
    PolymorphicProxySerializer,
    extend_schema,
    extend_schema_view,
)
from rest_framework import serializers
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.throttling import SimpleRateThrottle
from rest_framework.views import APIView

from config import composition
from config.api import ListQuery, StrictSerializer, validated
from tapme.businesses.point_scope import request_scope
from tapme.messaging.infrastructure.processing import receive
from tapme.messaging.schemas import (
    ChannelOutput,
    ChatFolderListOutput,
    ChatFolderOutput,
    ChatMessageOutput,
    ChatPaymentOutput,
    ConversationDetailOutput,
    ConversationListOutput,
    ConversationOutput,
    MessageListOutput,
    OkOutput,
    QuickReplyOutput,
    SummaryOutput,
)
from tapme.shared.domain import InvalidInput


class ConnectInput(StrictSerializer):
    phone_number_id = serializers.RegexField(r"^[0-9]{5,80}$")
    waba_id = serializers.RegexField(r"^[0-9]{5,80}$", required=False, default="")
    app_secret = serializers.CharField(max_length=512, required=False, default="", write_only=True)
    version = serializers.IntegerField(min_value=0, required=False)
    token = serializers.CharField(max_length=4096, trim_whitespace=True, write_only=True)


class ChatQuery(ListQuery):
    search = serializers.CharField(max_length=150, required=False, allow_blank=True)
    category = serializers.ChoiceField(choices=["all", "waiting", "mine", "closed"], default="all")
    folder_id = serializers.UUIDField(required=False)


class MessageQuery(StrictSerializer):
    before = serializers.IntegerField(min_value=0, default=0)
    after = serializers.IntegerField(min_value=0, default=0)
    limit = serializers.IntegerField(min_value=1, max_value=100, default=50)


class SendInput(StrictSerializer):
    text = serializers.CharField(max_length=4096)
    request_id = serializers.UUIDField()
    reply_to_id = serializers.IntegerField(
        min_value=1, max_value=2**63 - 1, required=False, allow_null=True, default=None
    )


class ReadInput(StrictSerializer):
    last_message_id = serializers.IntegerField(min_value=0)


class StartInput(StrictSerializer):
    customer_id = serializers.UUIDField()


class UpdateInput(StrictSerializer):
    version = serializers.IntegerField(min_value=1)
    assigned_to = serializers.UUIDField(required=False, allow_null=True)
    mode = serializers.ChoiceField(choices=["human", "closed"], required=False)
    customer_id = serializers.UUIDField(required=False)
    customer_name = serializers.CharField(max_length=150, required=False)


class AttachmentInput(StrictSerializer):
    file = serializers.FileField()
    text = serializers.CharField(max_length=1024, required=False, default="", allow_blank=True)
    request_id = serializers.UUIDField()
    reply_to_id = serializers.IntegerField(
        min_value=1, max_value=2**63 - 1, required=False, allow_null=True, default=None
    )


class ChatAPIView(APIView):
    def run(self, request, business_id, operation, **data):
        return Response(
            composition.chats().run(operation, request_scope(request, business_id), **data)
        )


class ChannelView(ChatAPIView):
    def get(self, request, business_id):
        return self.run(request, business_id, "channel")

    def post(self, request, business_id):
        if not request.is_secure() and request.get_host().split(":")[0] not in {
            "127.0.0.1",
            "localhost",
            "testserver",
        }:
            raise InvalidInput(
                "Для передачи токена откройте CRM по HTTPS или на самом сервере через localhost."
            )
        return self.run(request, business_id, "connect", **validated(ConnectInput, request.data))

    def delete(self, request, business_id):
        return self.run(request, business_id, "disconnect")


class ChatListView(ChatAPIView):
    def get(self, request, business_id):
        return self.run(
            request, business_id, "listing", **validated(ChatQuery, request.query_params)
        )

    def post(self, request, business_id):
        return self.run(request, business_id, "start", **validated(StartInput, request.data))


class ChatDetailView(ChatAPIView):
    def get(self, request, business_id, chat_id):
        return self.run(request, business_id, "detail", chat_id=chat_id)

    def patch(self, request, business_id, chat_id):
        return self.run(
            request, business_id, "update", chat_id=chat_id, **validated(UpdateInput, request.data)
        )


class FolderCreateInput(StrictSerializer):
    name = serializers.CharField(max_length=40)


class FolderVersionInput(StrictSerializer):
    version = serializers.IntegerField(min_value=1)


class FolderUpdateInput(FolderCreateInput, FolderVersionInput):
    pass


class ChatFoldersInput(StrictSerializer):
    version = serializers.IntegerField(min_value=1)
    folder_ids = serializers.ListField(child=serializers.UUIDField(), max_length=30)


class ChatFolderListView(ChatAPIView):
    @extend_schema(operation_id="chat_folder_list", responses=ChatFolderListOutput)
    def get(self, request, business_id):
        return self.run(request, business_id, "folders")

    @extend_schema(request=FolderCreateInput, responses=ChatFolderOutput)
    def post(self, request, business_id):
        return self.run(
            request, business_id, "create_folder", **validated(FolderCreateInput, request.data)
        )


class ChatFolderDetailView(ChatAPIView):
    @extend_schema(request=FolderUpdateInput, responses=OkOutput)
    def patch(self, request, business_id, folder_id):
        return self.run(
            request,
            business_id,
            "rename_folder",
            folder_id=folder_id,
            **validated(FolderUpdateInput, request.data),
        )

    @extend_schema(request=FolderVersionInput, responses=OkOutput)
    def delete(self, request, business_id, folder_id):
        return self.run(
            request,
            business_id,
            "delete_folder",
            folder_id=folder_id,
            **validated(FolderVersionInput, request.data),
        )


class ChatFoldersView(ChatAPIView):
    @extend_schema(request=ChatFoldersInput, responses=ConversationDetailOutput)
    def put(self, request, business_id, chat_id):
        return self.run(
            request,
            business_id,
            "set_chat_folders",
            chat_id=chat_id,
            **validated(ChatFoldersInput, request.data),
        )


class ChatMessagesView(ChatAPIView):
    def get(self, request, business_id, chat_id):
        return self.run(
            request,
            business_id,
            "messages",
            chat_id=chat_id,
            **validated(MessageQuery, request.query_params),
        )

    def post(self, request, business_id, chat_id):
        return self.run(
            request, business_id, "send", chat_id=chat_id, **validated(SendInput, request.data)
        )


class ChatReadView(ChatAPIView):
    def post(self, request, business_id, chat_id):
        return self.run(
            request, business_id, "read", chat_id=chat_id, **validated(ReadInput, request.data)
        )


class ChatRetryView(ChatAPIView):
    def post(self, request, business_id, chat_id, message_id):
        return self.run(request, business_id, "retry", chat_id=chat_id, message_id=message_id)


class ChatAttachmentView(ChatAPIView):
    def post(self, request, business_id, chat_id):
        data = validated(AttachmentInput, request.data)
        file = data.pop("file")
        if file.size > 16 * 1024 * 1024:
            raise InvalidInput("Вложение должно быть не больше 16 МБ.")
        return self.run(
            request,
            business_id,
            "attach",
            chat_id=chat_id,
            content=file.read(),
            mime=file.content_type,
            name=file.name,
            **data,
        )


class ChatFileView(APIView):
    def get(self, request, business_id, chat_id, message_id):
        result = composition.chats().run(
            "file", request_scope(request, business_id), chat_id=chat_id, message_id=message_id
        )
        response = HttpResponse(result["content"], content_type=result["mime"])
        response["Content-Disposition"] = content_disposition_header(
            result["mime"] == "application/pdf", result["name"]
        )
        response["X-Content-Type-Options"] = "nosniff"
        response["Cache-Control"] = "private, no-store"
        return response


class WebhookThrottle(SimpleRateThrottle):
    rate = "300/min"
    scope = "meta-webhook"

    def get_cache_key(self, request, view):
        return self.cache_format % {
            "scope": self.scope,
            "ident": request.META.get("REMOTE_ADDR", "unknown"),
        }


@csrf_exempt
def whatsapp_webhook(request, webhook_key=None):
    throttle = WebhookThrottle()
    if not throttle.allow_request(request, None):
        response = HttpResponse(status=429)
        response["Retry-After"] = str(max(1, int(throttle.wait() or 60)))
        return response
    from django.utils import timezone

    from tapme.messaging.models import ChannelAccount

    channel = None
    verify_token = settings.META_WEBHOOK_VERIFY_TOKEN
    if webhook_key:
        channel = (
            ChannelAccount.objects.filter(webhook_key=webhook_key, status="active")
            .exclude(app_secret_encrypted="")
            .first()
        )
        if not channel:
            return HttpResponse(status=404)
        verify_token = channel.verify_token
    if not channel and (not settings.META_APP_SECRET or not verify_token):
        return HttpResponse(status=503)
    if request.method == "GET":
        valid = request.GET.get("hub.mode") == "subscribe" and hmac.compare_digest(
            request.GET.get("hub.verify_token", "").encode(),
            verify_token.encode(),
        )
        if valid and channel:
            ChannelAccount.objects.filter(id=channel.id).update(webhook_verified_at=timezone.now())
        return (
            HttpResponse(request.GET.get("hub.challenge", ""), content_type="text/plain")
            if valid
            else HttpResponse(status=403)
        )
    if request.method != "POST":
        return HttpResponse(status=405)
    if len(request.body) > 1024 * 1024:
        return HttpResponse(status=413)
    try:
        accepted = receive(request.body, request.headers.get("X-Hub-Signature-256", ""), channel)
    except (ValueError, json.JSONDecodeError, InvalidInput):
        return HttpResponse(status=400)
    return JsonResponse({"received": True}) if accepted else HttpResponse(status=401)


class RegisterInput(StrictSerializer):
    pin = serializers.RegexField(r"^[0-9]{6}$", write_only=True)


class AutoreplyInput(StrictSerializer):
    version = serializers.IntegerField(min_value=1)
    enabled = serializers.BooleanField()
    start = serializers.RegexField(r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")
    end = serializers.RegexField(r"^(?:[01][0-9]|2[0-3]):[0-5][0-9]$")
    open_text = serializers.CharField(max_length=4096)
    closed_text = serializers.CharField(max_length=4096)


class PaymentSettingsInput(StrictSerializer):
    version = serializers.IntegerField(min_value=1)
    note = serializers.CharField(max_length=150, allow_blank=True)
    text = serializers.CharField(max_length=1024)
    file = serializers.FileField(required=False)
    remove = serializers.BooleanField(default=False)


class QuickReplyInput(StrictSerializer):
    title = serializers.CharField(max_length=100)
    text = serializers.CharField(max_length=4096)
    version = serializers.IntegerField(min_value=1, required=False)
    sort_order = serializers.IntegerField(min_value=0, max_value=10000, default=0)


class VersionInput(StrictSerializer):
    version = serializers.IntegerField(min_value=1)


class ChatPaymentInput(StrictSerializer):
    amount = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=Decimal("0.01"))
    order_id = serializers.UUIDField(required=False, allow_null=True)
    request_id = serializers.UUIDField()


class SimulationInput(StrictSerializer):
    phone = serializers.RegexField(r"^\+[1-9][0-9]{7,14}$")
    text = serializers.CharField(max_length=4096)
    name = serializers.CharField(max_length=150)


class ChannelActionView(ChatAPIView):
    def post(self, request, business_id, action):
        if action not in {
            "register",
            "subscribe",
            "check",
            "autoreply",
            "simulate",
            "simulate-verify",
        }:
            from tapme.shared.domain import NotFound

            raise NotFound("Действие не найдено.")
        if action == "autoreply":
            return self.run(
                request, business_id, "save_autoreply", **validated(AutoreplyInput, request.data)
            )
        if action == "simulate":
            return self.run(
                request, business_id, "simulate", **validated(SimulationInput, request.data)
            )
        if action == "simulate-verify":
            return self.run(request, business_id, "simulate_verify")
        return self.run(
            request,
            business_id,
            action,
            **(validated(RegisterInput, request.data) if action == "register" else {}),
        )


class PaymentSettingsView(ChatAPIView):
    def post(self, request, business_id):
        data = validated(PaymentSettingsInput, request.data)
        file = data.pop("file", None)
        if file:
            if file.size > 5 * 1024 * 1024:
                raise InvalidInput("QR должен быть не больше 5 МБ.")
            data.update(content=file.read(), mime=file.content_type)
        return self.run(request, business_id, "save_payment", **data)

    def get(self, request, business_id):
        result = composition.chats().run("payment_file", request_scope(request, business_id))
        response = HttpResponse(result["content"], content_type=result["mime"])
        response["Cache-Control"] = "private, no-store"
        response["X-Content-Type-Options"] = "nosniff"
        return response


class QuickReplyView(ChatAPIView):
    def get(self, request, business_id):
        return self.run(request, business_id, "quick_replies")

    def post(self, request, business_id):
        return self.run(
            request, business_id, "save_quick_reply", **validated(QuickReplyInput, request.data)
        )


class QuickReplyDetailView(ChatAPIView):
    def patch(self, request, business_id, reply_id):
        return self.run(
            request,
            business_id,
            "save_quick_reply",
            reply_id=reply_id,
            **validated(QuickReplyInput, request.data),
        )

    def delete(self, request, business_id, reply_id):
        return self.run(
            request,
            business_id,
            "delete_quick_reply",
            reply_id=reply_id,
            **validated(VersionInput, request.data),
        )


class ChatPaymentView(ChatAPIView):
    def get(self, request, business_id, chat_id):
        return self.run(request, business_id, "payment_options", chat_id=chat_id)

    def post(self, request, business_id, chat_id):
        return self.run(
            request,
            business_id,
            "send_payment",
            chat_id=chat_id,
            **validated(ChatPaymentInput, request.data),
        )


class SummaryInput(StrictSerializer):
    after = serializers.IntegerField(min_value=0, default=0)


class ChatSummaryView(ChatAPIView):
    def get(self, request, business_id):
        return self.run(
            request, business_id, "summary", **validated(SummaryInput, request.query_params)
        )


# These explicit schemas document the existing URL contract rather than introducing aliases.

ChannelView = extend_schema_view(
    get=extend_schema(responses=ChannelOutput),
    post=extend_schema(
        operation_id="whatsapp_connect", request=ConnectInput, responses=ChannelOutput
    ),
    delete=extend_schema(responses=ChannelOutput),
)(ChannelView)
ChatListView = extend_schema_view(
    get=extend_schema(
        operation_id="chat_list", parameters=[ChatQuery], responses=ConversationListOutput
    ),
    post=extend_schema(request=StartInput, responses=ConversationOutput),
)(ChatListView)
ChatDetailView = extend_schema_view(
    get=extend_schema(responses=ConversationDetailOutput),
    patch=extend_schema(request=UpdateInput, responses=ConversationDetailOutput),
)(ChatDetailView)
ChatMessagesView = extend_schema_view(
    get=extend_schema(parameters=[MessageQuery], responses=MessageListOutput),
    post=extend_schema(request=SendInput, responses=ChatMessageOutput),
)(ChatMessagesView)
ChatReadView = extend_schema_view(post=extend_schema(request=ReadInput, responses=OkOutput))(
    ChatReadView
)
ChatRetryView = extend_schema_view(post=extend_schema(request=None, responses=ChatMessageOutput))(
    ChatRetryView
)
ChatAttachmentView = extend_schema_view(
    post=extend_schema(request=AttachmentInput, responses=ChatMessageOutput)
)(ChatAttachmentView)
ChatFileView = extend_schema_view(get=extend_schema(responses=OpenApiTypes.BINARY))(ChatFileView)
PaymentSettingsView = extend_schema_view(
    get=extend_schema(responses={(200, "image/jpeg"): OpenApiTypes.BINARY}),
    post=extend_schema(request=PaymentSettingsInput, responses=ChatPaymentOutput),
)(PaymentSettingsView)
ChatPaymentView = extend_schema_view(
    get=extend_schema(responses=ChatPaymentOutput),
    post=extend_schema(request=ChatPaymentInput, responses=ChatMessageOutput),
)(ChatPaymentView)
QuickReplyView = extend_schema_view(
    get=extend_schema(operation_id="quick_reply_list", responses=QuickReplyOutput(many=True)),
    post=extend_schema(request=QuickReplyInput, responses=QuickReplyOutput),
)(QuickReplyView)
QuickReplyDetailView = extend_schema_view(
    patch=extend_schema(request=QuickReplyInput, responses=QuickReplyOutput),
    delete=extend_schema(request=VersionInput, responses=OkOutput),
)(QuickReplyDetailView)
ChatSummaryView = extend_schema_view(
    get=extend_schema(parameters=[SummaryInput], responses=SummaryOutput)
)(ChatSummaryView)
ChannelActionView = extend_schema_view(
    post=extend_schema(
        operation_id="whatsapp_channel_action",
        description="register: PIN; autoreply: policy + version; simulate: phone/name/text. subscribe, check, simulate-verify: empty body. simulate returns {ok:true}; other actions return channel status.",
        request=PolymorphicProxySerializer(
            component_name="ChannelAction",
            serializers=[RegisterInput, AutoreplyInput, SimulationInput],
            resource_type_field_name=None,
        ),
        responses=PolymorphicProxySerializer(
            component_name="ChannelActionResult",
            serializers=[ChannelOutput, OkOutput],
            resource_type_field_name=None,
        ),
    )
)(ChannelActionView)


class ChannelWebhookView(APIView):
    authentication_classes = []
    permission_classes = [AllowAny]
    throttle_classes = []  # Signature endpoint has its own 300/minute IP limit.

    @extend_schema(
        operation_id="whatsapp_webhook_verify",
        auth=[],
        responses=OpenApiTypes.STR,
        parameters=[
            OpenApiParameter(name=name, required=True, type=str)
            for name in ["hub.mode", "hub.verify_token", "hub.challenge"]
        ],
    )
    def get(self, request, webhook_key):
        return whatsapp_webhook(request, webhook_key)

    @extend_schema(
        operation_id="whatsapp_webhook_receive",
        parameters=[
            OpenApiParameter(
                name="X-Hub-Signature-256",
                location=OpenApiParameter.HEADER,
                required=True,
                type=str,
            )
        ],
        auth=[],
        request=OpenApiTypes.OBJECT,
        responses=OpenApiTypes.OBJECT,
    )
    def post(self, request, webhook_key):
        return whatsapp_webhook(request, webhook_key)
