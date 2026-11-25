"""Place at: backend/accounts/middleware.py

A person who signed in with Google has a Django user but none of the health answers the alerts
need. Until they fill them in, send them to /complete-profile/.
"""
from django.shortcuts import redirect

from .models import UserProfile

EXEMPT = ("/complete-profile/", "/logout/", "/signed-out/", "/accounts/", "/admin/", "/static/", "/api/")


class ProfileRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        u = request.user
        if (u.is_authenticated and not u.is_superuser and not request.path.startswith(EXEMPT)
                and not UserProfile.objects.filter(user=u).exists()):
            return redirect("complete-profile")
        return self.get_response(request)
