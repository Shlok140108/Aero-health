from django.contrib import admin

from .models import UserProfile


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "age", "gender", "occupation", "city", "pregnancy_status", "created_at")
    list_filter = ("occupation", "gender", "pregnancy_status")
    search_fields = ("user__username", "user__email", "city")
