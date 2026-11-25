from django.contrib import admin
from django.urls import path, include
from django.views.generic import RedirectView

urlpatterns = [
    path("admin/", admin.site.urls),
    path("api/weather/", include("weather.urls")),
    path("api/alerts/", include("alerts.urls")),
    path("accounts/login/", RedirectView.as_view(url="/login/", query_string=True)),
    path("accounts/signup/", RedirectView.as_view(url="/signup/")),
    path("accounts/", include("allauth.urls")),      # /accounts/google/login/ and its callback
    path("", include("accounts.urls")),
    path("", include("backend.dashboard.urls")),
]