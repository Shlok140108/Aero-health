"""Place at: backend/accounts/models.py

One UserProfile per Django User. Django's own User table keeps username / password (hashed) /
email / first_name; everything the health alerts need lives here.
"""
from django.conf import settings
from django.core.validators import MaxValueValidator, MinValueValidator
from django.db import models

GENDERS = [("F", "Female"), ("M", "Male"), ("O", "Other / prefer not to say")]

OCCUPATIONS = [
    ("outdoor_labour", "Outdoor labourer (construction, roads, loading)"),
    ("farmer", "Farmer / agricultural worker"),
    ("driver", "Driver, delivery rider or street vendor"),
    ("factory", "Factory / industrial worker"),
    ("healthcare", "Healthcare worker"),
    ("office", "Office / indoor work"),
    ("student", "Student"),
    ("homemaker", "Homemaker"),
    ("retired", "Retired"),
    ("other", "Something else"),
]
# occupations that are outdoors by nature (used by the alert rules)
OUTDOOR_OCCUPATIONS = {"outdoor_labour", "farmer", "driver"}

OUTDOOR_HOURS = [(0, "Almost none"), (2, "1-2 hours"), (4, "3-5 hours"), (7, "6-8 hours"), (10, "More than 8 hours")]

PREGNANCY = [
    ("na", "Not applicable"),
    ("no", "Not pregnant"),
    ("pregnant", "Pregnant"),
    ("nursing", "Breastfeeding / recently gave birth"),
]
TRIMESTERS = [(1, "First (weeks 1-13)"), (2, "Second (weeks 14-27)"), (3, "Third (week 28 onwards)")]

CONDITIONS = [
    ("asthma", "Asthma"),
    ("copd", "COPD / chronic bronchitis"),
    ("heart", "Heart condition"),
    ("bp", "High blood pressure"),
    ("diabetes", "Diabetes"),
    ("allergy", "Dust / pollen allergy"),
    ("kidney", "Kidney disease"),
    ("skin_eye", "Eczema / eye irritation"),
]


class UserProfile(models.Model):
    user = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile")

    # step 2: contact
    age = models.PositiveSmallIntegerField(validators=[MinValueValidator(13), MaxValueValidator(100)])
    phone = models.CharField(max_length=16)                       # stored as +91XXXXXXXXXX
    notify_email = models.BooleanField(default=True)
    notify_sms = models.BooleanField(default=False)

    # step 3: work + pregnancy
    gender = models.CharField(max_length=1, choices=GENDERS)
    occupation = models.CharField(max_length=20, choices=OCCUPATIONS)
    job_title = models.CharField(max_length=100, blank=True)
    outdoor_hours = models.PositiveSmallIntegerField(choices=OUTDOOR_HOURS, default=0)
    pregnancy_status = models.CharField(max_length=10, choices=PREGNANCY, default="na")
    trimester = models.PositiveSmallIntegerField(choices=TRIMESTERS, null=True, blank=True)

    # step 4: health
    conditions = models.JSONField(default=list, blank=True)       # list of codes from CONDITIONS
    smoker = models.BooleanField(default=False)
    breathless_in_smog = models.BooleanField(default=False)

    # step 5: home location
    city = models.CharField(max_length=120, blank=True)
    state = models.CharField(max_length=80, blank=True)
    lat = models.FloatField(null=True, blank=True)
    lon = models.FloatField(null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    # AeroHealth alert preferences. Medical details remain in the existing broad profile fields.
    alert_language = models.CharField(max_length=5, choices=[("en", "English"), ("hi", "Hindi"), ("mr", "Marathi"), ("ta", "Tamil"), ("bn", "Bengali")], default="en")
    guidance_sensitivity = models.CharField(max_length=12, choices=[("standard", "Standard"), ("sensitive", "Sensitive"), ("high", "Highly sensitive")], default="standard")
    alerts_enabled = models.BooleanField(default=False)
    weather_updates_enabled = models.BooleanField(default=False)
    alerts_consent_at = models.DateTimeField(null=True, blank=True)
    push_enabled = models.BooleanField(default=False)
    fcm_token = models.CharField(max_length=500, blank=True)
    voice_enabled = models.BooleanField(default=False)
    phone_verified_at = models.DateTimeField(null=True, blank=True)
    otp_hash = models.CharField(max_length=64, blank=True)
    otp_expires_at = models.DateTimeField(null=True, blank=True)
    otp_sent_at = models.DateTimeField(null=True, blank=True)
    otp_attempts = models.PositiveSmallIntegerField(default=0)
    quiet_start = models.TimeField(null=True, blank=True)
    quiet_end = models.TimeField(null=True, blank=True)
    alert_timezone = models.CharField(max_length=40, default="Asia/Kolkata")
    max_alerts_per_day = models.PositiveSmallIntegerField(default=4, validators=[MinValueValidator(1), MaxValueValidator(20)])
    # Expanded onboarding questionnaire answers; sensitive answers require explicit consent.
    kyc_data = models.JSONField(default=dict, blank=True)
    kyc_completed = models.BooleanField(default=False)

    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        if self.pk:
            previous = type(self).objects.filter(pk=self.pk).values_list("phone", flat=True).first()
            if previous is not None and previous != self.phone:
                self.phone_verified_at = None
                self.otp_hash = ""
                self.otp_expires_at = None
                self.otp_attempts = 0
        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.user.username} ({self.age})"
