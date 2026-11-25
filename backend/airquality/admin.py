from django.contrib import admin
from .models import Location, GroundReading, AQIGridPoint

@admin.register(Location)
class LocationAdmin(admin.ModelAdmin):
    list_display = ("name", "state", "is_cpcb_station", "lat", "lon")
    list_filter = ("is_cpcb_station", "state")
    search_fields = ("name", "state")

@admin.register(GroundReading)
class GroundReadingAdmin(admin.ModelAdmin):
    list_display = ("location", "aqi", "source", "timestamp")
    list_filter = ("source",)
    date_hierarchy = "timestamp"

@admin.register(AQIGridPoint)
class AQIGridPointAdmin(admin.ModelAdmin):
    list_display = ("aqi", "source", "model_version", "lat", "lon", "timestamp")
    list_filter = ("source", "model_version")
    date_hierarchy = "timestamp"
