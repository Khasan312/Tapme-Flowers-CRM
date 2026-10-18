import secrets
import uuid

from django.conf import settings
from django.db import models
from django.utils import timezone


def webhook_token():
    return secrets.token_urlsafe(32)


def default_autoreply():
    return {
        "enabled": True,
        "start": "09:00",
        "end": "20:00",
        "open_text": "Здравствуйте! Это {магазин} 🌷 Менеджер ответит в течение 10 минут.",
        "closed_text": "Здравствуйте! Сейчас мы закрыты. Ответим в рабочее время. Можно оставить заказ здесь.",
    }


class ChannelAccount(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.OneToOneField("businesses.Business", on_delete=models.PROTECT)
    phone_number_id = models.CharField(max_length=80, unique=True)
    display_phone = models.CharField(max_length=40)
    display_name = models.CharField(max_length=150)
    token_encrypted = models.TextField()
    status = models.CharField(max_length=20, default="active")
    connected_at = models.DateTimeField(default=timezone.now)
    last_webhook_at = models.DateTimeField(null=True)
    waba_id = models.CharField(max_length=80, blank=True)
    app_secret_encrypted = models.TextField(blank=True)
    webhook_key = models.CharField(max_length=64, default=webhook_token, unique=True)
    verify_token = models.CharField(max_length=64, default=webhook_token)
    webhook_verified_at = models.DateTimeField(null=True)
    registered_at = models.DateTimeField(null=True)
    subscribed_at = models.DateTimeField(null=True)
    token_checked_at = models.DateTimeField(null=True)
    last_inbound_at = models.DateTimeField(null=True)
    quality_rating = models.CharField(max_length=30, blank=True)
    connection_error = models.CharField(max_length=300, blank=True)
    provider_mode = models.CharField(max_length=10, default="live")
    autoreply = models.JSONField(default=default_autoreply)
    version = models.PositiveIntegerField(default=1)


class Conversation(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    channel = models.ForeignKey(ChannelAccount, on_delete=models.CASCADE)
    customer = models.ForeignKey("customers.CustomerRecord", null=True, on_delete=models.PROTECT)
    phone = models.CharField(max_length=16)
    profile_name = models.CharField(max_length=150, blank=True)
    needs_customer_link = models.BooleanField(default=False)
    assigned_to = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    version = models.PositiveIntegerField(default=1)
    mode = models.CharField(max_length=10, default="human")
    waiting_since = models.DateTimeField(null=True)
    last_inbound_at = models.DateTimeField(null=True)
    last_message_at = models.DateTimeField(default=timezone.now)
    last_message_preview = models.CharField(max_length=160, blank=True)
    opted_out = models.BooleanField(default=False)
    created_at = models.DateTimeField(default=timezone.now)
    autoreplied_at = models.DateTimeField(null=True)
    customer_created = models.BooleanField(default=False)
    customer_name_confirmed = models.BooleanField(default=False)
    provider_read_message_id = models.BigIntegerField(default=0)
    provider_read_sent_id = models.BigIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["channel", "phone"], name="chat_channel_phone")
        ]
        indexes = [models.Index(fields=["channel", "last_message_at"])]


class Message(models.Model):
    id = models.BigAutoField(primary_key=True)
    conversation = models.ForeignKey(
        Conversation, on_delete=models.CASCADE, related_name="messages"
    )
    # Provider IDs and client request IDs are both scoped to the channel/conversation.
    external_id = models.CharField(max_length=500, null=True)
    request_id = models.UUIDField(default=uuid.uuid4)
    delivery_key = models.UUIDField(default=uuid.uuid4, unique=True)
    direction = models.CharField(max_length=10)
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
    kind = models.CharField(max_length=30, default="text")
    text = models.TextField(blank=True)
    payload = models.JSONField(default=dict)
    status = models.CharField(max_length=20, default="queued")
    error = models.CharField(max_length=300, blank=True)
    happened_at = models.DateTimeField(default=timezone.now)
    created_at = models.DateTimeField(default=timezone.now)
    sending_at = models.DateTimeField(null=True)
    media_key = models.CharField(max_length=500, blank=True)
    media_type = models.CharField(max_length=100, blank=True)
    media_name = models.CharField(max_length=150, blank=True)
    automated = models.BooleanField(default=False)
    context_id = models.CharField(max_length=500, blank=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["conversation", "external_id"], name="chat_external_message"
            ),
            models.UniqueConstraint(
                fields=["conversation", "request_id"], name="chat_request_once"
            ),
        ]
        indexes = [
            models.Index(fields=["conversation", "id"]),
            models.Index(fields=["status", "created_at"]),
        ]


class ConversationRead(models.Model):
    conversation = models.ForeignKey(Conversation, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    last_message_id = models.BigIntegerField(default=0)

    class Meta:
        constraints = [
            models.UniqueConstraint(fields=["conversation", "user"], name="chat_read_user")
        ]


class WebhookEvent(models.Model):
    digest = models.CharField(primary_key=True, max_length=64)
    payload = models.JSONField()
    received_at = models.DateTimeField(default=timezone.now)
    processed_at = models.DateTimeField(null=True)
    attempts = models.PositiveSmallIntegerField(default=0)
    error = models.CharField(max_length=200, blank=True)
    channel = models.ForeignKey(ChannelAccount, null=True, on_delete=models.CASCADE)


class QuickReply(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    business = models.ForeignKey("businesses.Business", on_delete=models.CASCADE)
    title = models.CharField(max_length=100)
    text = models.TextField()
    sort = models.PositiveIntegerField(default=0)
    version = models.PositiveIntegerField(default=1)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, on_delete=models.SET_NULL)
