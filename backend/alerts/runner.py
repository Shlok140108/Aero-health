import logging, uuid
from collections import Counter
from copy import copy
from django.conf import settings
from django.db.models import Q
from django.utils import timezone
from .conditions import Conditions
from .engine import evaluate_rules, channels_for, block_reason, Decision
from .models import AlertLog, AlertState
from .personas import ensure_default_rules, sensitivity_threshold
from .templates import render, render_weather_update
from . import channels

logger=logging.getLogger(__name__)

def is_dry_run(override=None): return getattr(settings,"ALERTS_DRY_RUN",True) if override is None else override

def deliver(profile,decision,now,dry_run):
    event=uuid.uuid4(); rows=[]
    for channel in decision.channels or []:
        msg=render(profile,decision,channel)
        row=AlertLog(profile=profile,rule=decision.rule, event_id=event,alert_type=decision.alert_type,channel=channel,
            status=AlertLog.DRY_RUN if dry_run else AlertLog.FAILED,severity=decision.severity,language=profile.alert_language,
            title=msg.title,message=msg.body,aqi_value=decision.aqi,data_source=decision.source or "",
            data_timestamp=decision.data_timestamp,prediction_for=decision.prediction_for,model_version=decision.model_version,
            uncertainty_low=decision.uncertainty_low,uncertainty_high=decision.uncertainty_high,
            location_label=decision.location_label,location_lat=decision.location_lat,location_lon=decision.location_lon)
        if not dry_run:
            try: row.provider_id=str(channels.send_via(channel,profile,msg) or "")[:120]; row.status=AlertLog.SENT
            except Exception as exc: row.status=AlertLog.FAILED; row.error=str(exc)[:500]; logger.warning("Alert channel %s failed: %s",channel,exc)
        row.save(); rows.append(row)
    return rows


def process_weather_update(profile, now, dry_run, weather_cache, summary):
    if not profile.weather_updates_enabled:
        return
    if not profile.kyc_data.get("location_consent"):
        summary["weather_updates_skipped"]["location_consent"] += 1
        return
    if not profile.push_enabled or not profile.fcm_token:
        summary["weather_updates_skipped"]["push_not_enabled"] += 1
        return

    lat, lon = round(profile.lat, 2), round(profile.lon, 2)
    key = (lat, lon)
    if key not in weather_cache:
        try:
            from dashboard.live import fetch_current_weather
            weather_cache[key] = fetch_current_weather(lat, lon)
        except Exception:
            logger.exception("Weather update data fetch failed for profile %s", profile.pk)
            summary["weather_update_failures"] += 1
            weather_cache[key] = None
    weather = weather_cache[key]
    if weather is None:
        return

    place = ", ".join(part for part in (profile.city, profile.state) if part) or "your location"
    place = place[:120]
    message = render_weather_update(profile, weather, place)
    row = AlertLog(
        profile=profile,
        event_id=uuid.uuid4(),
        alert_type=AlertLog.WEATHER_UPDATE,
        channel="push",
        status=AlertLog.DRY_RUN if dry_run else AlertLog.FAILED,
        language=profile.alert_language,
        title=message.title,
        message=message.body,
        data_source="Open-Meteo",
        data_timestamp=now,
        location_label=place,
        location_lat=lat,
        location_lon=lon,
    )
    if not dry_run:
        try:
            row.provider_id = str(channels.send_via("push", profile, message) or "")[:120]
            row.status = AlertLog.SENT
        except Exception as exc:
            row.error = str(exc)[:500]
            logger.warning("Weather push failed for profile %s: %s", profile.pk, exc)
    row.save()
    summary["logs"][row.status] += 1
    if row.status == AlertLog.SENT:
        summary["weather_updates_sent"] += 1
    elif row.status == AlertLog.DRY_RUN:
        summary["weather_updates_dry_run"] += 1
    else:
        summary["weather_update_failures"] += 1


def process_profile(profile,now,dry_run,cache,summary):
    if profile.lat is None or profile.lon is None:
        if profile.weather_updates_enabled or profile.alerts_enabled:
            summary["skipped_no_location"]+=1
        return
    process_weather_update(profile, now, dry_run, summary["weather_cache"], summary)
    if not profile.alerts_enabled or not profile.alerts_consent_at:
        return
    ensure_default_rules(profile)
    locations=[("Home",profile.lat,profile.lon)]
    locations += [(x.name,x.lat,x.lon) for x in profile.saved_alert_locations.filter(is_active=True)]
    for label,lat,lon in locations:
        cond=Conditions(lat,lon,now,cache); rules=list(profile.alert_rules.all()); decisions=evaluate_rules(rules,cond)
        current=cond.aqi(); state=AlertState.objects.filter(profile=profile,location_label=label,alert_type="current_aqi").first()
        current_rule=next((r for r in rules if r.alert_type=="current_aqi" and r.is_active),None)
        if not any(d.alert_type=="current_aqi" for d in decisions) and state and state.is_active and current and current_rule:
            threshold=sensitivity_threshold(current_rule.aqi_threshold,profile.guidance_sensitivity)
            if current["value"] < threshold:
                clear=Decision(current_rule,"all_clear",1,aqi=current["value"],source=current["source"],place=label,data_timestamp=current.get("timestamp"),location_label=label,location_lat=lat,location_lon=lon)
                clear.channels=[]
                if profile.push_enabled and profile.fcm_token: clear.channels.append("push")
                if profile.notify_sms and profile.phone and profile.phone_verified_at: clear.channels.append("sms")
                if not block_reason(profile,clear,now,label) and clear.channels:
                    rows=deliver(profile,clear,now,dry_run)
                    for row in rows: summary["logs"][row.status]+=1
                    if any(r.status in (AlertLog.SENT,AlertLog.DRY_RUN) for r in rows):
                        state.is_active=False; state.last_aqi=current["value"]; state.save()
        sent=0
        for d in decisions:
            d.location_label,d.location_lat,d.location_lon=label,lat,lon; d.place=d.place or label
            d.channels=channels_for(profile,d)
            reason=block_reason(profile,d,now,label)
            if reason: summary["suppressed"][reason]+=1; continue
            if sent >= getattr(settings,"ALERTS_MAX_ALERTS_PER_RUN",1): summary["suppressed"]["per_run_limit"]+=1; continue
            rows=deliver(profile,d,now,dry_run); sent+=1
            for row in rows: summary["logs"][row.status]+=1
            if any(r.status in (AlertLog.SENT,AlertLog.DRY_RUN) for r in rows):
                summary["alerts"]+=1
                if d.alert_type=="current_aqi": AlertState.objects.update_or_create(profile=profile,location_label=label,alert_type="current_aqi",defaults={"is_active":True,"last_severity":d.severity,"last_aqi":d.aqi})
        if current is None: summary["no_data"]+=1

def evaluate_profiles(profiles=None,now=None,dry_run=None):
    now=now or timezone.now(); dry_run=is_dry_run(dry_run)
    if profiles is None:
        from accounts.models import UserProfile
        profiles=UserProfile.objects.filter(
            Q(alerts_enabled=True, alerts_consent_at__isnull=False) | Q(weather_updates_enabled=True)
        )
    summary={"dry_run":dry_run,"profiles":0,"alerts":0,"weather_updates_sent":0,"weather_updates_dry_run":0,
             "weather_update_failures":0,"weather_updates_skipped":Counter(),"no_data":0,
             "skipped_no_location":0,"logs":Counter(),"suppressed":Counter(),"weather_cache":{}}
    condition_cache={}
    for profile in profiles.prefetch_related("alert_rules","saved_alert_locations"):
        summary["profiles"]+=1
        try: process_profile(profile,now,dry_run,condition_cache,summary)
        except Exception: logger.exception("Alert evaluation failed for account profile %s",profile.pk); summary["suppressed"]["error"]+=1
    summary["logs"]=dict(summary["logs"]); summary["suppressed"]=dict(summary["suppressed"])
    summary["weather_updates_skipped"]=dict(summary["weather_updates_skipped"])
    summary.pop("weather_cache")
    return summary
