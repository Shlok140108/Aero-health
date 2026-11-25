from django.urls import path
from . import views
app_name="alerts"
urlpatterns=[
 path("settings/",views.SettingsView.as_view(),name="settings"),
 path("rules/",views.RulesView.as_view(),name="rules"), path("rules/<int:pk>/",views.RulesView.as_view(),name="rule-detail"),
 path("logs/",views.LogsView.as_view(),name="logs"), path("locations/",views.SavedLocationsView.as_view(),name="locations"), path("locations/<int:pk>/",views.SavedLocationDetailView.as_view(),name="location-detail"),
 path("preview/",views.PreviewView.as_view(),name="preview"), path("evaluate/",views.EvaluateView.as_view(),name="evaluate"), path("stats/",views.StatsView.as_view(),name="stats"),
 path("phone/request-otp/",views.PhoneOtpRequestView.as_view(),name="phone-request-otp"), path("phone/confirm-otp/",views.PhoneOtpConfirmView.as_view(),name="phone-confirm-otp"),
 path("webhooks/twilio-sms/",views.twilio_sms_webhook,name="twilio-sms-webhook"),
 path("organizations/",views.OrganizationCreateView.as_view(),name="organization-create"), path("organizations/<int:pk>/join/",views.OrganizationJoinView.as_view(),name="organization-join"), path("organizations/<int:pk>/dashboard/",views.OrganizationDashboardView.as_view(),name="organization-dashboard"),
]
