"""Place at: backend/accounts/forms.py"""
import re

from django import forms
from django.contrib.auth import get_user_model, password_validation
from django.contrib.auth.forms import AuthenticationForm
from django.db import transaction

from .models import CONDITIONS, PREGNANCY, UserProfile

User = get_user_model()
PREGNANCY_MIN_AGE, PREGNANCY_MAX_AGE = 13, 55


class HealthProfileForm(forms.ModelForm):
    """Everything about the person except the login details (shared by sign-up and Account page)."""

    conditions = forms.MultipleChoiceField(
        label="Do any of these apply to you?", choices=CONDITIONS + [("none", "None of these")],
        widget=forms.CheckboxSelectMultiple, required=True,
        error_messages={"required": "Choose at least one, or 'None of these'."})
    pregnancy_status = forms.ChoiceField(
        label="Are you pregnant?", choices=[c for c in PREGNANCY if c[0] != "na"], required=False)

    class Meta:
        model = UserProfile
        fields = ["age", "phone", "notify_email", "notify_sms", "gender", "occupation", "job_title",
                  "outdoor_hours", "pregnancy_status", "trimester", "conditions", "smoker",
                  "breathless_in_smog", "city", "state", "lat", "lon"]
        labels = {
            "age": "Your age", "phone": "Mobile number", "gender": "Gender",
            "occupation": "What do you do?", "job_title": "Job title or work (optional)",
            "outdoor_hours": "Time spent outdoors on a typical day", "trimester": "Which trimester?",
            "smoker": "I smoke", "breathless_in_smog": "I often cough or feel breathless in dusty or smoggy air",
            "city": "Your city or area", "state": "State",
            "notify_email": "Email me alerts", "notify_sms": "Text me alerts (SMS)",
        }
        widgets = {"lat": forms.HiddenInput, "lon": forms.HiddenInput,
                   "age": forms.NumberInput(attrs={"min": 13, "max": 100, "inputmode": "numeric"}),
                   "phone": forms.TextInput(attrs={"type": "tel", "placeholder": "98765 43210", "autocomplete": "tel"}),
                   "city": forms.TextInput(attrs={"list": "city-list", "autocomplete": "off"})}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["gender"].choices = [("", "Select…")] + [c for c in self.fields["gender"].choices if c[0]]
        self.fields["occupation"].choices = [("", "Select…")] + [c for c in self.fields["occupation"].choices if c[0]]
        self.fields["trimester"].choices = [("", "Select…")] + [c for c in self.fields["trimester"].choices if c[0] != ""]
        self.fields["pregnancy_status"].widget = forms.RadioSelect(choices=self.fields["pregnancy_status"].choices)
        for name, f in self.fields.items():
            w = f.widget
            if not isinstance(w, (forms.CheckboxInput, forms.CheckboxSelectMultiple, forms.RadioSelect, forms.HiddenInput)):
                w.attrs.setdefault("class", "field")

    # --- cleaning -------------------------------------------------------------------------
    def clean_phone(self):
        digits = re.sub(r"\D", "", self.cleaned_data["phone"])
        if len(digits) == 12 and digits.startswith("91"):
            digits = digits[2:]
        elif len(digits) == 11 and digits.startswith("0"):
            digits = digits[1:]
        if not re.fullmatch(r"[6-9]\d{9}", digits):
            raise forms.ValidationError("Enter a 10-digit Indian mobile number.")
        return "+91" + digits

    def clean_conditions(self):
        picked = [c for c in self.cleaned_data["conditions"] if c != "none"]
        return picked                                     # 'none' (or nothing else) -> []

    def clean(self):
        data = super().clean()
        age, gender = data.get("age"), data.get("gender")
        can_be_pregnant = gender == "F" and age is not None and PREGNANCY_MIN_AGE <= age <= PREGNANCY_MAX_AGE
        if not can_be_pregnant:
            data["pregnancy_status"], data["trimester"] = "na", None
        else:
            status = data.get("pregnancy_status")
            if not status:
                self.add_error("pregnancy_status", "Please choose one.")
            elif status == "pregnant" and not data.get("trimester"):
                self.add_error("trimester", "Please choose your trimester.")
            if status != "pregnant":
                data["trimester"] = None
        lat, lon = data.get("lat"), data.get("lon")
        if (lat is None) != (lon is None) or (lat is not None and not (-90 <= lat <= 90 and -180 <= lon <= 180)):
            data["lat"] = data["lon"] = None
        if not data.get("city") and data.get("lat") is None:
            self.add_error("city", "Tell us your city or use your current location.")
        return data


class SignupForm(HealthProfileForm):
    full_name = forms.CharField(label="Your name", max_length=100, widget=forms.TextInput(attrs={"autocomplete": "name"}))
    username = forms.CharField(label="Choose a username", min_length=3, max_length=30,
                               help_text="Letters, numbers, dot and underscore.",
                               widget=forms.TextInput(attrs={"autocomplete": "username", "autocapitalize": "none"}))
    email = forms.EmailField(label="Email address", widget=forms.EmailInput(attrs={"autocomplete": "email"}))
    password1 = forms.CharField(label="Password", strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))
    password2 = forms.CharField(label="Confirm password", strip=False, widget=forms.PasswordInput(attrs={"autocomplete": "new-password"}))

    field_order = ["full_name", "username", "password1", "password2", "age", "phone", "email",
                   "notify_email", "notify_sms"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for n in ("full_name", "username", "email", "password1", "password2"):
            self.fields[n].widget.attrs.setdefault("class", "field")

    def clean_username(self):
        u = self.cleaned_data["username"].strip()
        if not re.fullmatch(r"[A-Za-z0-9_.]+", u):
            raise forms.ValidationError("Use only letters, numbers, dot and underscore.")
        if User.objects.filter(username__iexact=u).exists():
            raise forms.ValidationError("That username is taken.")
        return u

    def clean_email(self):
        e = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=e).exists():
            raise forms.ValidationError("An account with this email already exists.")
        return e

    def clean(self):
        data = super().clean()
        p1, p2 = data.get("password1"), data.get("password2")
        if p1 and p2 and p1 != p2:
            self.add_error("password2", "Passwords don't match.")
        elif p1:
            tmp = User(username=data.get("username", ""), email=data.get("email", ""), first_name=data.get("full_name", ""))
            try:
                password_validation.validate_password(p1, tmp)
            except forms.ValidationError as e:
                self.add_error("password1", e)
        return data

    @transaction.atomic
    def save(self, commit=True):
        d = self.cleaned_data
        user = User.objects.create_user(d["username"], d["email"], d["password1"], first_name=d["full_name"])
        profile = super().save(commit=False)
        profile.user = user
        profile.save()
        return user


class ProfileForm(HealthProfileForm):
    """Account page: same questions, plus alert preferences and explicit consent."""
    full_name = forms.CharField(label="Your name", max_length=100)
    email = forms.EmailField(label="Email address")
    alert_language = forms.ChoiceField(label="Alert language", choices=[("en", "English"), ("hi", "Hindi"), ("mr", "Marathi"), ("ta", "Tamil"), ("bn", "Bengali")])
    guidance_sensitivity = forms.ChoiceField(label="Guidance sensitivity", choices=[("standard", "Standard"), ("sensitive", "Sensitive"), ("high", "Highly sensitive")])
    alerts_enabled = forms.BooleanField(label="Enable personalized AQI alerts", required=False)
    alerts_consent = forms.BooleanField(label="I consent to receive personalized environmental alerts", required=False)

    field_order = ["full_name", "email", "age", "phone", "notify_email", "notify_sms", "alert_language", "guidance_sensitivity", "alerts_enabled", "alerts_consent"]

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["full_name"].widget.attrs["class"] = "field"
        self.fields["email"].widget.attrs["class"] = "field"
        for field_name in ("alert_language", "guidance_sensitivity"):
            self.fields[field_name].widget.attrs["class"] = "field"
        self.fields["alerts_enabled"].initial = self.instance.alerts_enabled
        self.fields["alerts_consent"].initial = bool(self.instance.alerts_consent_at)
        user = self.instance.user
        self.fields["full_name"].initial = user.first_name
        self.fields["email"].initial = user.email

    def clean_email(self):
        e = self.cleaned_data["email"].strip().lower()
        if User.objects.filter(email__iexact=e).exclude(pk=self.instance.user_id).exists():
            raise forms.ValidationError("Another account already uses this email.")
        return e

    def clean(self):
        data = super().clean()
        if data.get("alerts_enabled") and not data.get("alerts_consent") and not self.instance.alerts_consent_at:
            self.add_error("alerts_consent", "Consent is required before enabling alerts.")
        if self.data.get("weather_updates_enabled") == "yes" and (data.get("lat") is None or data.get("lon") is None):
            self.add_error("city", "Choose a location with coordinates before enabling weather updates.")
        if data.get("alerts_enabled") and (data.get("lat") is None or data.get("lon") is None):
            self.add_error("alerts_enabled", "Set your current location before enabling alerts.")
        return data

    @transaction.atomic
    def save(self, commit=True):
        profile = super().save(commit=False)
        for field_name in ("alert_language", "guidance_sensitivity", "alerts_enabled"):
            setattr(profile, field_name, self.cleaned_data[field_name])
        profile.weather_updates_enabled = self.data.get("weather_updates_enabled") == "yes"
        if self.cleaned_data.get("alerts_consent"):
            if not profile.alerts_consent_at:
                from django.utils import timezone
                profile.alerts_consent_at = timezone.now()
        else:
            profile.alerts_enabled = False
            profile.alerts_consent_at = None
            profile.push_enabled = False
            profile.notify_sms = False
            profile.voice_enabled = False
        if commit:
            profile.save()
        user = profile.user
        user.first_name, user.email = self.cleaned_data["full_name"], self.cleaned_data["email"]
        user.save(update_fields=["first_name", "email"])
        return profile


class LoginForm(AuthenticationForm):
    username = forms.CharField(label="Username", widget=forms.TextInput(
        attrs={"class": "field", "autocomplete": "username", "autocapitalize": "none", "autofocus": True}))
    password = forms.CharField(label="Password", strip=False, widget=forms.PasswordInput(
        attrs={"class": "field", "autocomplete": "current-password"}))
    error_messages = {**AuthenticationForm.error_messages,
                      "invalid_login": "That username and password don't match. Please try again."}

    def clean_username(self):
        u = self.cleaned_data["username"].strip()
        match = User.objects.filter(username__iexact=u).first()      # so 'Shlok' and 'shlok' both work
        return match.username if match else u
