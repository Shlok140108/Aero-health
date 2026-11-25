from django.db import migrations, models
import django.core.validators

class Migration(migrations.Migration):
    dependencies = [("accounts", "0001_initial")]
    operations = [
        migrations.AddField("userprofile", "alert_language", models.CharField(choices=[("en", "English"), ("hi", "Hindi"), ("mr", "Marathi"), ("ta", "Tamil"), ("bn", "Bengali")], default="en", max_length=5)),
        migrations.AddField("userprofile", "guidance_sensitivity", models.CharField(choices=[("standard", "Standard"), ("sensitive", "Sensitive"), ("high", "Highly sensitive")], default="standard", max_length=12)),
        migrations.AddField("userprofile", "alerts_enabled", models.BooleanField(default=False)),
        migrations.AddField("userprofile", "alerts_consent_at", models.DateTimeField(blank=True, null=True)),
        migrations.AddField("userprofile", "push_enabled", models.BooleanField(default=False)),
        migrations.AddField("userprofile", "fcm_token", models.CharField(blank=True, max_length=255)),
        migrations.AddField("userprofile", "voice_enabled", models.BooleanField(default=False)),
        migrations.AddField("userprofile", "phone_verified_at", models.DateTimeField(blank=True, null=True)),
        migrations.AddField("userprofile", "otp_hash", models.CharField(blank=True, max_length=64)),
        migrations.AddField("userprofile", "otp_expires_at", models.DateTimeField(blank=True, null=True)),
        migrations.AddField("userprofile", "otp_sent_at", models.DateTimeField(blank=True, null=True)),
        migrations.AddField("userprofile", "otp_attempts", models.PositiveSmallIntegerField(default=0)),
        migrations.AddField("userprofile", "quiet_start", models.TimeField(blank=True, null=True)),
        migrations.AddField("userprofile", "quiet_end", models.TimeField(blank=True, null=True)),
        migrations.AddField("userprofile", "alert_timezone", models.CharField(default="Asia/Kolkata", max_length=40)),
        migrations.AddField("userprofile", "max_alerts_per_day", models.PositiveSmallIntegerField(default=4, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(20)])),
    ]
