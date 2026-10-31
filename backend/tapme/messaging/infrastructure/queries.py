from django.db.models import F, FilteredRelation, Q

from tapme.messaging.models import Message


def unread_messages(user_id):
    # Join the user's unique read marker once, rather than a subquery per message.
    return (
        Message.objects.filter(direction="in")
        .annotate(
            user_read=FilteredRelation(
                "conversation__conversationread",
                condition=Q(conversation__conversationread__user_id=user_id),
            )
        )
        .filter(Q(user_read__id__isnull=True) | Q(id__gt=F("user_read__last_message_id")))
    )
