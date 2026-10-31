"""Repair databases that applied 0004 before it retained SQL defaults.

0004 also retains the defaults from column creation, so fresh upgrades never
leave the old API/worker unable to INSERT between the two migrations.
"""

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("messaging", "0004_remove_conversation_chat_channel_phone_and_more")]

    operations = [
        migrations.RunSQL(
            sql=[
                "ALTER TABLE messaging_channelaccount ALTER COLUMN ig_username SET DEFAULT ''",
                "ALTER TABLE messaging_conversation ALTER COLUMN external_user_id SET DEFAULT ''",
            ],
            # Defaults are also part of the corrected 0004 state. Retaining them
            # on rollback is safe for both variants of that historical migration.
            reverse_sql=migrations.RunSQL.noop,
            state_operations=[
                migrations.AlterField(
                    model_name="channelaccount",
                    name="ig_username",
                    field=models.CharField(blank=True, db_default="", max_length=150),
                ),
                migrations.AlterField(
                    model_name="conversation",
                    name="external_user_id",
                    field=models.CharField(blank=True, db_default="", max_length=80),
                ),
            ],
        ),
    ]
