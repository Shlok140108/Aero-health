"""Place at: backend/accounts/urls.py"""
from django.urls import path

from . import views

urlpatterns = [
    path("signup/", views.signup, name="signup"),
    path("login/", views.login_view, name="login"),
    path("logout/", views.logout_view, name="logout"),
    path("signed-out/", views.signed_out, name="signed-out"),
    path("complete-profile/", views.complete_profile, name="complete-profile"),
    path("account/", views.account, name="account"),
]
