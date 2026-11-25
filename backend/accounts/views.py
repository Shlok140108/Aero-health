"""Place at: backend/accounts/views.py"""
from django.contrib.auth import login, logout
from django.contrib.auth.decorators import login_required
from django.shortcuts import redirect, render
from django.urls import reverse
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from . import health_rules
from .forms import HealthProfileForm, LoginForm, ProfileForm, SignupForm
from .models import UserProfile


def _safe_next(request):
    nxt = request.POST.get("next") or request.GET.get("next") or ""
    ok = url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}, require_https=request.is_secure())
    return nxt if ok and nxt else "/"


def signup(request):
    if request.user.is_authenticated:
        return redirect("/")
    form = SignupForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        user = form.save()
        login(request, user, backend="django.contrib.auth.backends.ModelBackend")
        return redirect("/")
    return render(request, "aerohealth/signup.html", {"form": form})


def login_view(request):
    if request.user.is_authenticated:
        return redirect("/")
    form = LoginForm(request, data=request.POST or None)
    if request.method == "POST" and form.is_valid():
        login(request, form.get_user())
        return redirect(_safe_next(request))
    return render(request, "aerohealth/auth.html", {"mode": "login", "form": form, "next": _safe_next(request)})


@require_POST
def logout_view(request):
    logout(request)
    return redirect("signed-out")


def signed_out(request):
    return render(request, "aerohealth/auth.html", {"mode": "out"})


@login_required
def account(request):
    try:
        profile = request.user.profile
    except UserProfile.DoesNotExist:                       # e.g. a superuser made with createsuperuser
        return redirect("/")
    form = ProfileForm(request.POST or None, instance=profile)
    saved = request.GET.get("saved") == "1"
    if request.method == "POST" and form.is_valid():
        form.save()
        # Save the extended KYC answers separately from the existing profile form.
        from django.db import transaction
        from django.utils import timezone

        fields = [
            "display_name", "age_group", "gender", "pregnant", "trimester",
            "pregnancy_complications", "live_alone", "mobility_support",
            "child_routine", "child_age_group", "location_permission", "home_area",
            "work_location", "travel_frequency", "health_conditions", "sensitivities",
            "medication", "smoking", "daily_routine", "outdoor_activities",
            "usual_outing_time", "transport", "home_equipment", "alert_types",
            "aqi_threshold", "notification_channels", "daily_summary_time", "language",
            "temperature_unit", "family_add", "family_members", "family_location_share",
            "family_permissions", "other_details",
        ]
        multi_fields = {"health_conditions", "sensitivities", "outdoor_activities", "home_equipment", "alert_types", "notification_channels", "family_members"}
        kyc = dict(profile.kyc_data or {})
        for key in fields:
            if key in multi_fields:
                kyc[key] = request.POST.getlist("kyc_" + key)
            elif "kyc_" + key in request.POST:
                kyc[key] = request.POST.get("kyc_" + key, "")

        basic_only = request.POST.get("kyc_basic_only") == "yes"
        health_ok = request.POST.get("kyc_health_consent") == "yes" and not basic_only
        location_ok = request.POST.get("kyc_location_consent") == "yes" and not basic_only
        kyc["basic_only"] = basic_only
        kyc["health_consent"] = health_ok
        kyc["location_consent"] = location_ok
        if not health_ok:
            for key in ("pregnant", "trimester", "pregnancy_complications", "health_conditions", "sensitivities", "medication", "smoking"):
                kyc.pop(key, None)
        if not location_ok:
            for key in ("location_permission", "home_area", "work_location", "family_location_share"):
                kyc.pop(key, None)
        kyc["consent_updated_at"] = timezone.now().isoformat()
        with transaction.atomic():
            profile.kyc_data = kyc
            profile.kyc_completed = bool(kyc.get("display_name") and kyc.get("age_group") and kyc.get("home_area"))
            profile.save(update_fields=["kyc_data", "kyc_completed", "updated_at"])
        return redirect(reverse("account") + "?saved=1")
    from alerts.personas import ensure_default_rules, sensitivity_threshold
    ensure_default_rules(profile)
    current_rule = profile.alert_rules.filter(alert_type="current_aqi").first()
    base_threshold = current_rule.aqi_threshold if current_rule else health_rules.aqi_threshold(profile)
    effective_threshold = sensitivity_threshold(base_threshold, profile.guidance_sensitivity)
    return render(request, "aerohealth/account.html", {
        "form": form, "saved": saved, "profile": profile,
        "persona": health_rules.persona(profile), "sensitivity": profile.get_guidance_sensitivity_display(),
        "threshold": effective_threshold})


@login_required
def complete_profile(request):
    """Google users land here once: same questions as sign-up, minus the account step."""
    if UserProfile.objects.filter(user=request.user).exists():
        return redirect("/")
    form = HealthProfileForm(request.POST or None)
    if request.method == "POST" and form.is_valid():
        profile = form.save(commit=False)
        profile.user = request.user
        profile.save()
        return redirect("/")
    return render(request, "aerohealth/signup.html", {
        "form": form, "social": True, "name": request.user.first_name or request.user.username})
