from datetime import timedelta
from unittest.mock import patch
from django.test import TestCase, override_settings
from django.contrib.auth import get_user_model
from django.utils import timezone
from accounts.models import UserProfile
from .models import AlertRule, AlertLog, SavedLocation
from .conditions import distance_km, Conditions
from .engine import evaluate_rules
from .personas import aqi_severity, persona_for_profile, ensure_default_rules

class AlertCoreTests(TestCase):
    def setUp(self):
        user=get_user_model().objects.create_user(username="alert-user",password="test-pass")
        self.profile=UserProfile.objects.create(user=user,age=28,phone="+919876543210",gender="O",occupation="office",lat=18.52,lon=73.85,alerts_enabled=True,alerts_consent_at=timezone.now())

    def test_cpcb_severity_bands(self):
        self.assertEqual([aqi_severity(x) for x in (25,75,150,250,350,450)],[0,1,2,3,4,5])

    def test_persona_derived_from_existing_account_profile(self):
        self.assertEqual(persona_for_profile(self.profile),"general")
        self.profile.conditions=["asthma"]
        self.assertEqual(persona_for_profile(self.profile),"asthma")

    def test_default_rules_created_once(self):
        ensure_default_rules(self.profile); ensure_default_rules(self.profile)
        self.assertEqual(self.profile.alert_rules.count(),4)

    def test_saved_locations_are_profile_scoped(self):
        loc=SavedLocation.objects.create(profile=self.profile,name="Office",lat=19.07,lon=72.87)
        self.assertEqual(self.profile.saved_alert_locations.get(pk=loc.pk).name,"Office")

    def test_distance_haversine(self):
        self.assertAlmostEqual(distance_km(0,0,0,1),111.19,delta=1)

    def test_forecast_uses_peak_record_time_not_first_hit(self):
        ensure_default_rules(self.profile)
        rule=self.profile.alert_rules.get(alert_type="forecast_aqi")
        rule.is_active=True; rule.aqi_threshold=100; rule.horizon_hours=72; rule.save()
        class FakeConditions:
            def aqi(self): return {"value":50,"source":"model_estimate"}
            def forecast(self):
                return [{"hours":8,"prediction":120,"forecast_for":timezone.now()+timedelta(hours=8),"place":"Pune"},
                        {"hours":20,"prediction":260,"forecast_for":timezone.now()+timedelta(hours=20),"place":"Pune"}]
        decisions=evaluate_rules([rule],FakeConditions())
        d=next(x for x in decisions if x.alert_type=="forecast_aqi")
        self.assertEqual(d.aqi,260); self.assertEqual(d.hours,20)

    def test_changing_phone_resets_verification(self):
        self.profile.phone_verified_at=timezone.now(); self.profile.save()
        self.profile.phone="+919876543211"; self.profile.save(); self.profile.refresh_from_db()
        self.assertIsNone(self.profile.phone_verified_at)

    @override_settings(ALERTS_DRY_RUN=True)
    def test_default_alerts_do_not_send_without_explicit_channels(self):
        self.assertFalse(self.profile.push_enabled)
        self.assertFalse(self.profile.notify_sms)
        self.assertFalse(self.profile.voice_enabled)
