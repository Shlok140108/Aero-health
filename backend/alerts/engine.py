from dataclasses import dataclass
from datetime import timedelta
from zoneinfo import ZoneInfo
from django.conf import settings
from django.db.models import Count
from .models import AlertLog
from .personas import VERY_POOR, aqi_severity, sensitivity_threshold

@dataclass
class Decision:
    rule: object
    alert_type: str
    severity: int
    aqi: float = None
    hours: int = None
    radius_km: int = None
    source: str = ""
    place: str = ""
    data_timestamp: object = None
    prediction_for: object = None
    model_version: str = ""
    uncertainty_low: float = None
    uncertainty_high: float = None
    channels: list = None
    location_label: str = "Home"
    location_lat: float = None
    location_lon: float = None


def evaluate_rules(rules, cond):
    out=[]
    for rule in rules:
        if not rule.is_active: continue
        threshold=sensitivity_threshold(rule.aqi_threshold, rule.profile.guidance_sensitivity)
        if rule.alert_type == "current_aqi":
            a=cond.aqi()
            if a and a["value"] >= threshold:
                out.append(Decision(rule, rule.alert_type, aqi_severity(a["value"]), aqi=a["value"], source=a["source"], place=a.get("place", ""), data_timestamp=a.get("timestamp"), model_version=a.get("model_version", ""), uncertainty_low=a.get("uncertainty_low"), uncertainty_high=a.get("uncertainty_high")))
        elif rule.alert_type == "forecast_aqi":
            current=cond.aqi()
            if current and current["value"] >= threshold: continue
            hits=[x for x in cond.forecast() if x["hours"] <= rule.horizon_hours and x["prediction"] >= threshold]
            if hits:
                peak=max(hits, key=lambda x:x["prediction"])
                out.append(Decision(rule, rule.alert_type, aqi_severity(peak["prediction"]), aqi=peak["prediction"], hours=peak["hours"], source="forecast", place=peak.get("place", ""), data_timestamp=peak.get("data_timestamp"), prediction_for=peak.get("forecast_for"), model_version=peak.get("model_version", ""), uncertainty_low=peak.get("uncertainty_low"), uncertainty_high=peak.get("uncertainty_high")))
        elif rule.alert_type == "smoke_arrival":
            smoke=cond.smoke(rule.radius_km)
            if smoke and smoke["hours"] <= rule.horizon_hours:
                out.append(Decision(rule, rule.alert_type, 3 if smoke["hours"] <= 6 else 2, hours=smoke["hours"], radius_km=rule.radius_km, source=smoke["source"], data_timestamp=smoke["timestamp"]))
        elif rule.alert_type == "stagnation":
            a,d=cond.aqi(),cond.dispersion()
            if a and d and d["poor"] and a["value"] >= threshold:
                out.append(Decision(rule, rule.alert_type, aqi_severity(a["value"]), aqi=a["value"], source=a["source"], place=a.get("place", ""), data_timestamp=a.get("timestamp"), model_version=a.get("model_version", ""), uncertainty_low=a.get("uncertainty_low"), uncertainty_high=a.get("uncertainty_high")))
    order={"current_aqi":0,"smoke_arrival":1,"forecast_aqi":2,"stagnation":3}
    return sorted(out,key=lambda x:(-x.severity,order.get(x.alert_type,9)))


def channels_for(profile, decision):
    result=[]
    if profile.push_enabled and profile.fcm_token: result.append("push")
    if profile.notify_sms and profile.phone and profile.phone_verified_at: result.append("sms")
    if profile.voice_enabled and profile.phone and profile.phone_verified_at and decision.rule.allow_voice and decision.aqi is not None and decision.aqi >= decision.rule.voice_min_aqi: result.append("voice")
    return result


def _local(profile, now):
    try: return now.astimezone(ZoneInfo(profile.alert_timezone or "Asia/Kolkata"))
    except Exception: return now.astimezone(ZoneInfo("Asia/Kolkata"))


def block_reason(profile, decision, now, location_label):
    if not profile.alerts_enabled or not profile.alerts_consent_at: return "no_consent"
    if not decision.channels: return "no_channel"
    if profile.quiet_start and profile.quiet_end and decision.severity < VERY_POOR:
        t=_local(profile,now).time(); start,end=profile.quiet_start,profile.quiet_end
        quiet=(start <= t < end) if start < end else (t >= start or t < end)
        if quiet: return "quiet_hours"
    logs=AlertLog.objects.filter(profile=profile, status__in=["sent","dry_run"])
    day_start=_local(profile,now).replace(hour=0,minute=0,second=0,microsecond=0)
    if logs.filter(created_at__gte=day_start).aggregate(n=Count("event_id",distinct=True))["n"] >= profile.max_alerts_per_day: return "daily_cap"
    same=logs.filter(alert_type=decision.alert_type,location_label=location_label)
    last=same.first()
    if last and now-last.created_at < timedelta(hours=decision.rule.cooldown_hours) and decision.severity <= last.severity: return "cooldown"
    if AlertLog.objects.filter(profile=profile,alert_type=decision.alert_type,location_label=location_label,status="failed",created_at__gte=now-timedelta(minutes=30)).exists(): return "retry_backoff"
    return None
