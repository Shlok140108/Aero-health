import hashlib, hmac, os, secrets
from datetime import timedelta
from django.conf import settings
from django.http import HttpResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.db.models import Count
from django.utils import timezone
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from .models import AlertRule, AlertLog, SavedLocation, Organization, OrganizationMember
from .serializers import AlertSettingsSerializer, RuleSerializer, LogSerializer, SavedLocationSerializer
from .personas import ensure_default_rules, persona_for_profile
from .conditions import Conditions
from .engine import evaluate_rules
from .templates import render
from .runner import evaluate_profiles


def get_profile(request):
    try: return request.user.profile
    except Exception: return None

class SettingsView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        p=get_profile(request)
        if not p: return Response({"error":"Complete your account profile first."},status=404)
        ensure_default_rules(p)
        return Response({"alerts_enabled":p.alerts_enabled,"consent":bool(p.alerts_consent_at),"language":p.alert_language,
            "persona":persona_for_profile(p),"guidance_sensitivity":p.guidance_sensitivity,"push_enabled":p.push_enabled,
            "push_token_registered":bool(p.fcm_token),"sms_enabled":p.notify_sms,"voice_enabled":p.voice_enabled,
            "phone_verified":bool(p.phone_verified_at),"quiet_start":p.quiet_start,"quiet_end":p.quiet_end,
            "timezone":p.alert_timezone,"max_alerts_per_day":p.max_alerts_per_day})
    def patch(self,request):
        p=get_profile(request)
        if not p: return Response({"error":"Complete your account profile first."},status=404)
        ser=AlertSettingsSerializer(data=request.data,partial=True,context={"profile":p}); ser.is_valid(raise_exception=True)
        data=ser.validated_data; consent_supplied="consent" in data; consent=data.pop("consent",False)
        for key,value in data.items(): setattr(p,key,value)
        if consent_supplied and consent and not p.alerts_consent_at: p.alerts_consent_at=timezone.now()
        if consent_supplied and not consent:
            p.alerts_enabled=False; p.alerts_consent_at=None
            p.push_enabled=False; p.notify_sms=False; p.voice_enabled=False
        p.save()
        ensure_default_rules(p)
        return self.get(request)

class RulesView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        p=get_profile(request)
        if not p: return Response({"error":"Profile missing"},status=404)
        ensure_default_rules(p); return Response(RuleSerializer(p.alert_rules.all(),many=True).data)
    def patch(self,request,pk):
        p=get_profile(request); rule=p.alert_rules.filter(pk=pk).first() if p else None
        if not rule: return Response({"error":"Rule not found"},status=404)
        ser=RuleSerializer(rule,data=request.data,partial=True); ser.is_valid(raise_exception=True)
        return Response(RuleSerializer(ser.save()).data)

class LogsView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        p=get_profile(request)
        if not p: return Response({"error":"Profile missing"},status=404)
        try: limit=max(1,min(int(request.query_params.get("limit",50)),200))
        except ValueError: limit=50
        return Response(LogSerializer(p.alert_logs.all()[:limit],many=True).data)

class SavedLocationsView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request):
        p=get_profile(request); return Response(SavedLocationSerializer(p.saved_alert_locations.all(),many=True).data if p else [])
    def post(self,request):
        p=get_profile(request)
        if not p: return Response({"error":"Profile missing"},status=404)
        if p.saved_alert_locations.count()>=20: return Response({"error":"Maximum 20 saved locations."},status=400)
        ser=SavedLocationSerializer(data=request.data); ser.is_valid(raise_exception=True)
        row=ser.save(profile=p); return Response(SavedLocationSerializer(row).data,status=201)

class SavedLocationDetailView(APIView):
    permission_classes=[IsAuthenticated]
    def delete(self,request,pk):
        p=get_profile(request); deleted,_=p.saved_alert_locations.filter(pk=pk).delete() if p else (0,{})
        return Response(status=204 if deleted else 404)

class PreviewView(APIView):
    permission_classes=[IsAuthenticated]
    def post(self,request):
        p=get_profile(request)
        if not p: return Response({"error":"Complete your profile first."},status=404)
        try: lat=float(request.data.get("lat",p.lat)); lon=float(request.data.get("lon",p.lon))
        except (TypeError,ValueError): return Response({"error":"Valid lat/lon are required."},status=400)
        if not (-90<=lat<=90 and -180<=lon<=180): return Response({"error":"Coordinates out of range."},status=400)
        ensure_default_rules(p); cond=Conditions(lat,lon); decisions=evaluate_rules(p.alert_rules.all(),cond); results=[]
        for d in decisions:
            msg=render(p,d,"push"); results.append({"type":d.alert_type,"aqi":d.aqi,"severity":d.severity,"title":msg.title,"message":msg.body,"source":d.source})
        return Response({"current_aqi":cond.aqi(),"alerts":results,"note":"Preview only; no notification was sent."})

class EvaluateView(APIView):
    permission_classes=[IsAdminUser]
    def post(self,request):
        dry=getattr(settings,"ALERTS_DRY_RUN",True) or bool(request.data.get("dry_run",False))
        return Response(evaluate_profiles(dry_run=dry))

class StatsView(APIView):
    permission_classes=[IsAdminUser]
    def get(self,request):
        since=timezone.now()-timedelta(hours=24); logs=AlertLog.objects.filter(created_at__gte=since)
        return Response({"dry_run_mode":getattr(settings,"ALERTS_DRY_RUN",True),"enabled_profiles":__import__("accounts.models",fromlist=["UserProfile"]).UserProfile.objects.filter(alerts_enabled=True).count(),
            "last_24h":{"by_status":list(logs.values("status").annotate(total=Count("id"))),"by_type":list(logs.values("alert_type").annotate(total=Count("id"))),"by_channel":list(logs.values("channel").annotate(total=Count("id")))}})

class OrganizationCreateView(APIView):
    permission_classes=[IsAuthenticated]
    def post(self,request):
        p=get_profile(request)
        if not p or not p.alerts_consent_at: return Response({"error":"Enable alerts and provide consent first."},status=403)
        name=str(request.data.get("name","")).strip()
        if not name or len(name)>160: return Response({"error":"Organization name is required (max 160 chars)."},status=400)
        org=Organization.objects.create(name=name); OrganizationMember.objects.create(organization=org,profile=p,role="admin")
        return Response({"id":org.id,"name":org.name,"role":"admin"},status=201)

class OrganizationJoinView(APIView):
    permission_classes=[IsAuthenticated]
    def post(self,request,pk):
        p=get_profile(request)
        if not p or not p.alerts_consent_at: return Response({"error":"Consent is required."},status=403)
        org=Organization.objects.filter(pk=pk,is_active=True).first()
        if not org: return Response({"error":"Organization not found."},status=404)
        _,created=OrganizationMember.objects.get_or_create(organization=org,profile=p,defaults={"role":"member"})
        return Response({"organization":org.name,"joined":created})

class OrganizationDashboardView(APIView):
    permission_classes=[IsAuthenticated]
    def get(self,request,pk):
        p=get_profile(request); membership=OrganizationMember.objects.filter(organization_id=pk,profile=p).select_related("organization").first() if p else None
        if not membership: return Response({"error":"Organization membership required."},status=403)
        since=timezone.now()-timedelta(hours=24); ids=OrganizationMember.objects.filter(organization_id=pk).values_list("profile_id",flat=True)
        logs=AlertLog.objects.filter(profile_id__in=ids,created_at__gte=since)
        member_count=len(ids)
        if member_count < 3:
            grouped=[]
            privacy_note="At least three opted-in members are required before aggregate alert breakdowns are displayed."
        else:
            grouped=list(logs.values("location_label","alert_type","status").annotate(
                total=Count("id"), distinct_members=Count("profile_id",distinct=True)
            ).filter(distinct_members__gte=3))
            privacy_note="Only location groups with at least three distinct opted-in members are shown; no individual health profiles are exposed."
        return Response({"organization":membership.organization.name,"window_hours":24,"member_count":member_count,"alerts_by_location":grouped,"privacy":privacy_note})

class PhoneOtpRequestView(APIView):
    permission_classes=[IsAuthenticated]
    def post(self,request):
        p=get_profile(request)
        if not p or not p.phone: return Response({"error":"Add a phone number to your account first."},status=400)
        now=timezone.now()
        if p.otp_sent_at and now-p.otp_sent_at<timedelta(minutes=1): return Response({"error":"Wait one minute before requesting another code."},status=429)
        code=f"{secrets.randbelow(1000000):06d}"; p.otp_hash=hashlib.sha256(code.encode()).hexdigest(); p.otp_expires_at=now+timedelta(minutes=5); p.otp_sent_at=now; p.otp_attempts=0; p.save()
        try:
            from twilio.rest import Client
            sid=getattr(settings,"ALERTS_TWILIO_SID",None) or os.environ.get("TWILIO_ACCOUNT_SID"); token=getattr(settings,"ALERTS_TWILIO_TOKEN",None) or os.environ.get("TWILIO_AUTH_TOKEN"); sender=getattr(settings,"ALERTS_TWILIO_FROM",None) or os.environ.get("TWILIO_FROM_NUMBER")
            if not (sid and token and sender): raise RuntimeError("Twilio is not configured")
            Client(sid,token).messages.create(to=p.phone,from_=sender,body=f"Your AeroHealth verification code is {code}. It expires in 5 minutes.")
        except Exception as exc:
            p.otp_hash=""; p.save(update_fields=["otp_hash"]); return Response({"error":f"OTP could not be sent: {exc}"},status=503)
        return Response({"message":"Verification code sent."})

class PhoneOtpConfirmView(APIView):
    permission_classes=[IsAuthenticated]
    def post(self,request):
        p=get_profile(request); code=str(request.data.get("code", ""))
        if not p or not p.otp_hash or not p.otp_expires_at or timezone.now()>p.otp_expires_at: return Response({"error":"Code expired. Request a new one."},status=400)
        if p.otp_attempts>=5: return Response({"error":"Too many attempts. Request a new code."},status=429)
        p.otp_attempts+=1
        if not hmac.compare_digest(p.otp_hash,hashlib.sha256(code.encode()).hexdigest()): p.save(update_fields=["otp_attempts"]); return Response({"error":"Incorrect code."},status=400)
        p.phone_verified_at=timezone.now(); p.otp_hash=""; p.otp_expires_at=None; p.otp_attempts=0; p.save()
        return Response({"verified":True})


@csrf_exempt
@require_POST
def twilio_sms_webhook(request):
    """Validated inbound Twilio STOP webhook; SMS/voice opt-out is honored immediately."""
    token=getattr(settings,"ALERTS_TWILIO_TOKEN",None) or os.environ.get("TWILIO_AUTH_TOKEN")
    if not token:
        return HttpResponse("Twilio is not configured",status=503)
    try:
        from twilio.request_validator import RequestValidator
        validator=RequestValidator(token)
        url=getattr(settings,"ALERTS_TWILIO_WEBHOOK_URL",None) or request.build_absolute_uri()
        if not validator.validate(url,request.POST,request.headers.get("X-Twilio-Signature","")):
            return HttpResponse("Invalid signature",status=403)
    except ImportError:
        return HttpResponse("Twilio SDK unavailable",status=503)
    body=request.POST.get("Body","").strip().lower()
    if body in {"stop","stopall","unsubscribe","cancel","end","quit","रोकें"}:
        from accounts.models import UserProfile
        UserProfile.objects.filter(phone=request.POST.get("From", "")).update(notify_sms=False,voice_enabled=False)
    return HttpResponse("<Response/>",content_type="text/xml")
