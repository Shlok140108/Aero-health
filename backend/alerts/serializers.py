from zoneinfo import ZoneInfo
from rest_framework import serializers
from .models import AlertRule, AlertLog, SavedLocation

class AlertSettingsSerializer(serializers.Serializer):
    alert_language=serializers.ChoiceField(choices=["en","hi","mr","ta","bn"],required=False)
    guidance_sensitivity=serializers.ChoiceField(choices=["standard","sensitive","high"],required=False)
    alerts_enabled=serializers.BooleanField(required=False)
    weather_updates_enabled=serializers.BooleanField(required=False)
    consent=serializers.BooleanField(write_only=True,required=False)
    push_enabled=serializers.BooleanField(required=False)
    fcm_token=serializers.CharField(max_length=500,allow_blank=True,required=False)
    notify_sms=serializers.BooleanField(required=False)
    voice_enabled=serializers.BooleanField(required=False)
    quiet_start=serializers.TimeField(allow_null=True,required=False)
    quiet_end=serializers.TimeField(allow_null=True,required=False)
    alert_timezone=serializers.CharField(max_length=40,required=False)
    max_alerts_per_day=serializers.IntegerField(min_value=1,max_value=20,required=False)
    def validate_alert_timezone(self,value):
        try: ZoneInfo(value)
        except Exception: raise serializers.ValidationError("Use a valid timezone such as Asia/Kolkata")
        return value
    def validate(self,attrs):
        profile=self.context.get("profile")
        start=attrs.get("quiet_start",getattr(profile,"quiet_start",None)); end=attrs.get("quiet_end",getattr(profile,"quiet_end",None))
        if bool(start)!=bool(end): raise serializers.ValidationError("Set both quiet hours or neither.")
        if attrs.get("alerts_enabled") and profile and not (profile.lat is not None and profile.lon is not None):
            raise serializers.ValidationError("Set your home location in Account before enabling alerts.")
        if attrs.get("weather_updates_enabled") and profile and not (profile.lat is not None and profile.lon is not None):
            raise serializers.ValidationError("Set your home location in Account before enabling weather updates.")
        if attrs.get("weather_updates_enabled") and profile and not profile.kyc_data.get("location_consent"):
            raise serializers.ValidationError({"weather_updates_enabled":"Enable location consent in Account before weather updates."})
        if attrs.get("push_enabled") and not attrs.get("fcm_token",getattr(profile,"fcm_token","")):
            raise serializers.ValidationError({"fcm_token":"Register a device token or disable push notifications."})
        if (attrs.get("notify_sms",getattr(profile,"notify_sms",False)) or attrs.get("voice_enabled",getattr(profile,"voice_enabled",False))) and not getattr(profile,"phone",""):
            raise serializers.ValidationError({"phone":"Add a phone number to your account first."})
        if attrs.get("alerts_enabled") and profile and not (attrs.get("consent") or profile.alerts_consent_at):
            raise serializers.ValidationError({"consent":"Explicit consent is required to enable alerts."})
        return attrs

class RuleSerializer(serializers.ModelSerializer):
    class Meta:
        model=AlertRule
        fields=["id","alert_type","is_active","aqi_threshold","horizon_hours","radius_km","cooldown_hours","allow_voice","voice_min_aqi"]
        read_only_fields=["id","alert_type"]

class LogSerializer(serializers.ModelSerializer):
    class Meta:
        model=AlertLog
        fields=["id","event_id","alert_type","channel","status","severity","language","title","message","aqi_value","data_source","data_timestamp","prediction_for","model_version","uncertainty_low","uncertainty_high","location_label","location_lat","location_lon","error","created_at"]

class SavedLocationSerializer(serializers.ModelSerializer):
    class Meta:
        model=SavedLocation
        fields=["id","name","lat","lon","is_active","created_at"]
        read_only_fields=["id","created_at"]
    def validate_name(self,v):
        v=v.strip()
        if not v: raise serializers.ValidationError("A location name is required.")
        return v
