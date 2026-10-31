"""Old WhatsApp workers must keep inserting throughout the Instagram upgrade."""

import pytest
from django.db import connection
from django.db.migrations.executor import MigrationExecutor


@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("repair_existing", [False, True])
def test_old_whatsapp_writes_immediately_after_instagram_migration(repair_existing):
    executor = MigrationExecutor(connection)
    latest = executor.loader.graph.leaf_nodes()
    previous = [("messaging", "0003_chat_folders")]
    target = [("messaging", "0004_remove_conversation_chat_channel_phone_and_more")]
    try:
        executor.migrate(previous)
        old = executor.loader.project_state(previous).apps
        business = old.get_model("businesses", "Business").objects.create(name="Rolling WhatsApp")
        channel = old.get_model("messaging", "ChannelAccount").objects.create(
            business_id=business.id, phone_number_id="11111111", display_name="Existing channel"
        )
        old_chat = old.get_model("messaging", "Conversation").objects.create(
            channel_id=channel.id, phone="+996700000001"
        )
        executor = MigrationExecutor(connection)
        executor.migrate(target)
        current = executor.loader.project_state(target).apps
        instagram = current.get_model("messaging", "ChannelAccount").objects.create(
            business_id=business.id,
            kind="instagram",
            phone_number_id=None,
            ig_user_id="123456789",
            ig_username="existing.profile",
        )
        ig_chat = current.get_model("messaging", "Conversation").objects.create(
            channel_id=instagram.id, phone="", external_user_id="987654321"
        )
        if repair_existing:
            # Reproduce a pilot DB on the original 0004; the follow-up migration
            # must repair it even though Django already marked 0004 applied.
            with connection.cursor() as cursor:
                cursor.execute(
                    "ALTER TABLE messaging_channelaccount ALTER COLUMN ig_username DROP DEFAULT"
                )
                cursor.execute(
                    "ALTER TABLE messaging_conversation ALTER COLUMN external_user_id DROP DEFAULT"
                )
            executor = MigrationExecutor(connection)
            target = [("messaging", "0005_rolling_instagram_defaults")]
            executor.migrate(target)
        # These models omit Instagram fields, just like the currently deployed release.
        chat = old.get_model("messaging", "Conversation").objects.create(
            channel_id=channel.id, phone="+996700000002"
        )
        new_business = old.get_model("businesses", "Business").objects.create(name="New channel")
        new_channel = old.get_model("messaging", "ChannelAccount").objects.create(
            business_id=new_business.id, phone_number_id="22222222"
        )
        current = executor.loader.project_state(target).apps
        assert (
            current.get_model("messaging", "Conversation").objects.get(id=chat.id).external_user_id
            == ""
        )
        assert (
            current.get_model("messaging", "Conversation").objects.get(id=old_chat.id).phone
            == old_chat.phone
        )
        account = current.get_model("messaging", "ChannelAccount").objects.get(id=new_channel.id)
        assert account.kind == "whatsapp" and account.ig_username == ""
        assert (
            current.get_model("messaging", "ChannelAccount")
            .objects.get(id=instagram.id)
            .ig_username
            == "existing.profile"
        )
        assert (
            current.get_model("messaging", "Conversation")
            .objects.get(id=ig_chat.id)
            .external_user_id
            == "987654321"
        )
    finally:
        MigrationExecutor(connection).migrate(latest)
