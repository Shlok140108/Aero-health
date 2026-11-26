"""Alert-domain models. User identity and health preferences stay in accounts.UserProfile."""
import uuid
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models


class AlertRule(models.Model):
    CURRENT_AQI = "current_aqi"
    FORECAST_AQI = "forecast_aqi"
    SMOKE_ARRIVAL = "smoke_arrival"
    STAGNATION = "stagnation"
    TYPES = [(CURRENT_AQI, "Current AQI"), (FORECAST_AQI, "Forecast AQI"),
             (SMOKE_ARRIVAL, "Smoke activity"), (STAGNATION, "Pollution stagnation")]
    profile = models.ForeignKey("accounts.UserProfile", on_delete=models.CASCADE, related_name="alert_rules")
    alert_type = models.CharField(max_length=20, choices=TYPES)
    is_active = models.BooleanField(default=True)
    aqi_threshold = models.PositiveSmallIntegerField(default=201, validators=[MinValueValidator(1), MaxValueValidator(500)])
    horizon_hours = models.PositiveSmallIntegerField(default=24, validators=[MinValueValidator(1), MaxValueValidator(72)])
    radius_km = models.PositiveSmallIntegerField(default=50, validators=[MinValueValidator(1), MaxValueValidator(300)])
    cooldown_hours = models.PositiveSmallIntegerField(default=6, validators=[MinValueValidator(1), MaxValueValidator(72)])
    allow_voice = models.BooleanField(default=False)
    voice_min_aqi = models.PositiveSmallIntegerField(default=301, validators=[MinValueValidator(1), MaxValueValidator(500)])

    class Meta:
        ordering = ["id"]
        constraints = [models.UniqueConstraint(fields=["profile", "alert_type"], name="uniq_alert_rule_type")]


class AlertLog(models.Model):
    SENT, DRY_RUN, FAILED = "sent", "dry_run", "failed"
    WEATHER_UPDATE = "weather_update"
    STATUS = [(SENT, "Sent"), (DRY_RUN, "Dry run"), (FAILED, "Failed")]
    profile = models.ForeignKey("accounts.UserProfile", on_delete=models.CASCADE, related_name="alert_logs")
    rule = models.ForeignKey(AlertRule, null=True, blank=True, on_delete=models.SET_NULL, related_name="logs")
    event_id = models.UUIDField(default=uuid.uuid4, db_index=True)
    alert_type = models.CharField(max_length=20)
    channel = models.CharField(max_length=10)
    status = models.CharField(max_length=10, choices=STATUS)
    severity = models.PositiveSmallIntegerField(default=0)
    language = models.CharField(max_length=5, default="en")
    title = models.CharField(max_length=200, blank=True)
    message = models.TextField(blank=True)
    aqi_value = models.FloatField(null=True, blank=True)
    data_source = models.CharField(max_length=40, blank=True)
    data_timestamp = models.DateTimeField(null=True, blank=True)
    prediction_for = models.DateTimeField(null=True, blank=True)
    model_version = models.CharField(max_length=80, blank=True)
    uncertainty_low = models.FloatField(null=True, blank=True)
    uncertainty_high = models.FloatField(null=True, blank=True)
    location_label = models.CharField(max_length=120, default="Home")
    location_lat = models.FloatField(null=True, blank=True)
    location_lon = models.FloatField(null=True, blank=True)
    provider_id = models.CharField(max_length=120, blank=True)
    error = models.CharField(max_length=500, blank=True)
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        ordering = ["-created_at", "-id"]
        indexes = [models.Index(fields=["profile", "alert_type", "-created_at"], name="alert_log_profile_type_idx")]


class SavedLocation(models.Model):
    profile = models.ForeignKey("accounts.UserProfile", on_delete=models.CASCADE, related_name="saved_alert_locations")
    name = models.CharField(max_length=120)
    lat = models.FloatField(validators=[MinValueValidator(-90), MaxValueValidator(90)])
    lon = models.FloatField(validators=[MinValueValidator(-180), MaxValueValidator(180)])
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["id"]
        constraints = [models.UniqueConstraint(fields=["profile", "name"], name="uniq_saved_alert_location")]


class AlertState(models.Model):
    profile = models.ForeignKey("accounts.UserProfile", on_delete=models.CASCADE, related_name="alert_states")
    location_label = models.CharField(max_length=120, default="Home")
    alert_type = models.CharField(max_length=20, default=AlertRule.CURRENT_AQI)
    is_active = models.BooleanField(default=False)
    last_severity = models.PositiveSmallIntegerField(default=0)
    last_aqi = models.FloatField(null=True, blank=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["profile", "location_label", "alert_type"], name="uniq_alert_state_location")]


class Organization(models.Model):
    """Employer workspace; dashboard exposes aggregates, never individual health profiles."""
    name = models.CharField(max_length=160)
    created_at = models.DateTimeField(auto_now_add=True)
    is_active = models.BooleanField(default=True)


class OrganizationMember(models.Model):
    organization = models.ForeignKey(Organization, on_delete=models.CASCADE, related_name="members")
    profile = models.ForeignKey("accounts.UserProfile", on_delete=models.CASCADE, related_name="alert_organizations")
    role = models.CharField(max_length=20, choices=[("admin", "Admin"), ("member", "Member")], default="member")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        constraints = [models.UniqueConstraint(fields=["organization", "profile"], name="uniq_alert_org_member")]


class MessageTemplate(models.Model):
    alert_type = models.CharField(max_length=20, choices=AlertRule.TYPES)
    language = models.CharField(max_length=5, choices=[("en", "English"), ("hi", "Hindi"), ("mr", "Marathi"), ("ta", "Tamil"), ("bn", "Bengali")])
    channel = models.CharField(max_length=10, choices=[("push", "Push"), ("sms", "SMS"), ("voice", "Voice")])
    title = models.CharField(max_length=200, blank=True)
    body = models.TextField()
    is_active = models.BooleanField(default=True)
    class Meta:
        constraints = [models.UniqueConstraint(fields=["alert_type", "language", "channel"], name="uniq_alert_message_template")]


class SmokeDriftPrediction(models.Model):
    """Ingestion target for a future FIRMS + plume-drift pipeline; no synthetic rows are created."""
    lat = models.FloatField()
    lon = models.FloatField()
    predicted_for = models.DateTimeField(db_index=True)
    generated_at = models.DateTimeField(db_index=True)
    hotspot_count = models.PositiveIntegerField(default=1)
    total_frp = models.FloatField(default=0)
    source = models.CharField(max_length=40, default="NASA FIRMS")
    model_version = models.CharField(max_length=80, blank=True)


class WeatherReading(models.Model):
    """Optional meteorological observations required for stagnation screening."""
    lat = models.FloatField()
    lon = models.FloatField()
    timestamp = models.DateTimeField(db_index=True)
    wind_speed_ms = models.FloatField(null=True, blank=True)
    boundary_layer_m = models.FloatField(null=True, blank=True)
    source = models.CharField(max_length=40, blank=True)
