from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("accounts", "0002_alert_preferences")]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="kyc_data",
            field=models.JSONField(blank=True, default=dict),
        ),
        migrations.AddField(
            model_name="userprofile",
            name="kyc_completed",
            field=models.BooleanField(default=False),
        ),
    ]
