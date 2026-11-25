import uuid
from django.db import migrations, models
import django.db.models.deletion
import django.core.validators

class Migration(migrations.Migration):
    initial = True
    dependencies = [("accounts", "0002_alert_preferences")]
    operations = [
        migrations.CreateModel(name="AlertRule", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("alert_type", models.CharField(choices=[("current_aqi", "Current AQI"), ("forecast_aqi", "Forecast AQI"), ("smoke_arrival", "Smoke activity"), ("stagnation", "Pollution stagnation")], max_length=20)),
            ("is_active", models.BooleanField(default=True)),
            ("aqi_threshold", models.PositiveSmallIntegerField(default=201, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(500)])),
            ("horizon_hours", models.PositiveSmallIntegerField(default=24, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(72)])),
            ("radius_km", models.PositiveSmallIntegerField(default=50, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(300)])),
            ("cooldown_hours", models.PositiveSmallIntegerField(default=6, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(72)])),
            ("allow_voice", models.BooleanField(default=False)),
            ("voice_min_aqi", models.PositiveSmallIntegerField(default=301, validators=[django.core.validators.MinValueValidator(1), django.core.validators.MaxValueValidator(500)])),
            ("profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="alert_rules", to="accounts.userprofile")),
        ], options={"ordering": ["id"], "constraints": [models.UniqueConstraint(fields=("profile", "alert_type"), name="uniq_alert_rule_type")]}),
        migrations.CreateModel(name="AlertLog", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
            ("event_id", models.UUIDField(db_index=True, default=uuid.uuid4)), ("alert_type", models.CharField(max_length=20)),
            ("channel", models.CharField(max_length=10)), ("status", models.CharField(choices=[("sent", "Sent"), ("dry_run", "Dry run"), ("failed", "Failed")], max_length=10)),
            ("severity", models.PositiveSmallIntegerField(default=0)), ("language", models.CharField(default="en", max_length=5)),
            ("title", models.CharField(blank=True, max_length=200)), ("message", models.TextField(blank=True)), ("aqi_value", models.FloatField(blank=True, null=True)),
            ("data_source", models.CharField(blank=True, max_length=40)), ("data_timestamp", models.DateTimeField(blank=True, null=True)),
            ("prediction_for", models.DateTimeField(blank=True, null=True)), ("model_version", models.CharField(blank=True, max_length=80)),
            ("uncertainty_low", models.FloatField(blank=True, null=True)), ("uncertainty_high", models.FloatField(blank=True, null=True)),
            ("location_label", models.CharField(default="Home", max_length=120)), ("location_lat", models.FloatField(blank=True, null=True)),
            ("location_lon", models.FloatField(blank=True, null=True)), ("provider_id", models.CharField(blank=True, max_length=120)),
            ("error", models.CharField(blank=True, max_length=500)), ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
            ("profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="alert_logs", to="accounts.userprofile")),
            ("rule", models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name="logs", to="alerts.alertrule")),
        ], options={"ordering": ["-created_at", "-id"], "indexes": [models.Index(fields=["profile", "alert_type", "-created_at"], name="alert_log_profile_type_idx")]}),
        migrations.CreateModel(name="SavedLocation", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("name", models.CharField(max_length=120)),
            ("lat", models.FloatField(validators=[django.core.validators.MinValueValidator(-90), django.core.validators.MaxValueValidator(90)])),
            ("lon", models.FloatField(validators=[django.core.validators.MinValueValidator(-180), django.core.validators.MaxValueValidator(180)])),
            ("is_active", models.BooleanField(default=True)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="saved_alert_locations", to="accounts.userprofile")),
        ], options={"ordering": ["id"], "constraints": [models.UniqueConstraint(fields=("profile", "name"), name="uniq_saved_alert_location")]}),
        migrations.CreateModel(name="AlertState", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("location_label", models.CharField(default="Home", max_length=120)),
            ("alert_type", models.CharField(default="current_aqi", max_length=20)), ("is_active", models.BooleanField(default=False)),
            ("last_severity", models.PositiveSmallIntegerField(default=0)), ("last_aqi", models.FloatField(blank=True, null=True)),
            ("updated_at", models.DateTimeField(auto_now=True)), ("profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="alert_states", to="accounts.userprofile")),
        ], options={"constraints": [models.UniqueConstraint(fields=("profile", "location_label", "alert_type"), name="uniq_alert_state_location")]}),
        migrations.CreateModel(name="Organization", fields=[("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("name", models.CharField(max_length=160)), ("created_at", models.DateTimeField(auto_now_add=True)), ("is_active", models.BooleanField(default=True))]),
        migrations.CreateModel(name="OrganizationMember", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("role", models.CharField(choices=[("admin", "Admin"), ("member", "Member")], default="member", max_length=20)), ("created_at", models.DateTimeField(auto_now_add=True)),
            ("organization", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="members", to="alerts.organization")),
            ("profile", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="alert_organizations", to="accounts.userprofile")),
        ], options={"constraints": [models.UniqueConstraint(fields=("organization", "profile"), name="uniq_alert_org_member")]}),
        migrations.CreateModel(name="MessageTemplate", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("alert_type", models.CharField(choices=[("current_aqi", "Current AQI"), ("forecast_aqi", "Forecast AQI"), ("smoke_arrival", "Smoke activity"), ("stagnation", "Pollution stagnation")], max_length=20)),
            ("language", models.CharField(choices=[("en", "English"), ("hi", "Hindi"), ("mr", "Marathi"), ("ta", "Tamil"), ("bn", "Bengali")], max_length=5)),
            ("channel", models.CharField(choices=[("push", "Push"), ("sms", "SMS"), ("voice", "Voice")], max_length=10)), ("title", models.CharField(blank=True, max_length=200)), ("body", models.TextField()), ("is_active", models.BooleanField(default=True)),
        ], options={"constraints": [models.UniqueConstraint(fields=("alert_type", "language", "channel"), name="uniq_alert_message_template")]}),
        migrations.CreateModel(name="SmokeDriftPrediction", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("lat", models.FloatField()), ("lon", models.FloatField()), ("predicted_for", models.DateTimeField(db_index=True)),
            ("generated_at", models.DateTimeField(db_index=True)), ("hotspot_count", models.PositiveIntegerField(default=1)), ("total_frp", models.FloatField(default=0)), ("source", models.CharField(default="NASA FIRMS", max_length=40)), ("model_version", models.CharField(blank=True, max_length=80)),
        ]),
        migrations.CreateModel(name="WeatherReading", fields=[
            ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")), ("lat", models.FloatField()), ("lon", models.FloatField()), ("timestamp", models.DateTimeField(db_index=True)),
            ("wind_speed_ms", models.FloatField(blank=True, null=True)), ("boundary_layer_m", models.FloatField(blank=True, null=True)), ("source", models.CharField(blank=True, max_length=40)),
        ]),
    ]
