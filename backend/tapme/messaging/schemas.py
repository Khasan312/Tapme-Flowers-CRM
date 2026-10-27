"""Public response contracts. Secrets are deliberately absent."""

from rest_framework import serializers


class ChatPaymentOutput(serializers.Serializer):
    version = serializers.IntegerField()
    note = serializers.CharField()
    text = serializers.CharField()
    image_url = serializers.CharField(allow_null=True)
    orders = serializers.ListField(child=serializers.DictField(), required=False)


class ChannelOutput(serializers.Serializer):
    configured = serializers.BooleanField()
    status = serializers.CharField()
    version = serializers.IntegerField()
    provider_mode = serializers.CharField()
    server_mode = serializers.CharField()
    simulator = serializers.BooleanField()
    display_name = serializers.CharField()
    display_phone = serializers.CharField()
    phone_number_id = serializers.CharField()
    waba_id = serializers.CharField()
    last_webhook_at = serializers.DateTimeField(allow_null=True)
    quality_rating = serializers.CharField()
    connection_error = serializers.CharField()
    autoreply = serializers.DictField(allow_null=True)
    checks = serializers.DictField(child=serializers.BooleanField())
    main_phone = serializers.CharField()
    payment = ChatPaymentOutput()
    webhook_path = serializers.CharField(required=False, help_text="Owner only")
    verify_token = serializers.CharField(
        required=False, help_text="Owner only; webhook verification token, not access token"
    )


class ConversationOutput(serializers.Serializer):
    id = serializers.UUIDField()
    customer_id = serializers.UUIDField(allow_null=True)
    name = serializers.CharField()
    phone = serializers.CharField()
    channel_phone = serializers.CharField()
    provider_mode = serializers.CharField()
    preview = serializers.CharField()
    last_message_at = serializers.DateTimeField()
    last_inbound_at = serializers.DateTimeField(allow_null=True)
    waiting_since = serializers.DateTimeField(allow_null=True)
    unread = serializers.IntegerField()
    mode = serializers.CharField()
    version = serializers.IntegerField()
    assigned_to = serializers.UUIDField(allow_null=True)
    assigned_name = serializers.CharField()
    needs_customer_link = serializers.BooleanField()
    new_customer = serializers.BooleanField()
    origin = serializers.CharField()
    can_reply = serializers.BooleanField()
    reply_reason = serializers.CharField()
    tags = serializers.ListField(child=serializers.CharField())
    folder_ids = serializers.ListField(child=serializers.UUIDField())


class ChatFolderOutput(serializers.Serializer):
    id = serializers.UUIDField()
    name = serializers.CharField()
    version = serializers.IntegerField()
    count = serializers.IntegerField()
    total = serializers.IntegerField()


class ChatFolderListOutput(serializers.Serializer):
    results = ChatFolderOutput(many=True)
    all_count = serializers.IntegerField()


class ConversationDetailOutput(ConversationOutput):
    customer = serializers.DictField(allow_null=True)
    staff = serializers.ListField(child=serializers.DictField())
    link_candidates = serializers.ListField(child=serializers.DictField())


class ConversationListOutput(serializers.Serializer):
    count = serializers.IntegerField()
    stats = serializers.DictField(child=serializers.IntegerField())
    results = ConversationOutput(many=True)


class ReplyMessageOutput(serializers.Serializer):
    id = serializers.CharField()
    text = serializers.CharField()
    direction = serializers.CharField()
    sender = serializers.CharField()
    kind = serializers.CharField()
    media_name = serializers.CharField()


class ChatMessageOutput(serializers.Serializer):
    id = serializers.CharField()
    request_id = serializers.UUIDField()
    direction = serializers.CharField()
    text = serializers.CharField()
    kind = serializers.CharField()
    status = serializers.CharField()
    error = serializers.CharField()
    sender = serializers.CharField()
    happened_at = serializers.DateTimeField()
    created_at = serializers.DateTimeField()
    media_url = serializers.CharField(allow_null=True)
    media_type = serializers.CharField()
    media_name = serializers.CharField()
    automated = serializers.BooleanField()
    context_id = serializers.CharField()
    external_id = serializers.CharField(allow_null=True)
    reply_to = ReplyMessageOutput(allow_null=True)


class MessageListOutput(serializers.Serializer):
    results = ChatMessageOutput(many=True)
    has_more = serializers.BooleanField()


class QuickReplyOutput(serializers.Serializer):
    id = serializers.UUIDField()
    title = serializers.CharField()
    text = serializers.CharField()
    version = serializers.IntegerField()
    sort_order = serializers.IntegerField()


class SummaryOutput(serializers.Serializer):
    waiting = serializers.IntegerField()
    unread = serializers.IntegerField()
    latest_inbound_id = serializers.CharField()
    items = serializers.ListField(child=serializers.DictField())


class OkOutput(serializers.Serializer):
    ok = serializers.BooleanField()
