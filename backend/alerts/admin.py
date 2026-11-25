from django.contrib import admin
from .models import AlertRule, AlertLog, SavedLocation, AlertState, Organization, OrganizationMember, MessageTemplate, SmokeDriftPrediction, WeatherReading

@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin): list_display=("profile","alert_type","is_active","aqi_threshold","cooldown_hours"); list_filter=("alert_type","is_active")
@admin.register(AlertLog)
class AlertLogAdmin(admin.ModelAdmin): list_display=("created_at","profile","alert_type","channel","status","aqi_value","data_source"); list_filter=("status","alert_type","channel"); readonly_fields=("created_at",)
admin.site.register([SavedLocation,AlertState,Organization,OrganizationMember,MessageTemplate,SmokeDriftPrediction,WeatherReading])
