from django.db import models


class Location(models.Model):
    name = models.CharField(max_length=200)
    lat = models.FloatField()
    lon = models.FloatField()
    state = models.CharField(max_length=100, blank=True)
    is_cpcb_station = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.name

class GroundReading(models.Model):
    """Timestamped AQI observation from a CPCB/OpenAQ monitoring station."""
    location = models.ForeignKey(Location, on_delete=models.CASCADE, related_name="ground_readings")
    aqi = models.FloatField(null=True, blank=True)
    timestamp = models.DateTimeField(db_index=True)
    source = models.CharField(max_length=30, default="CPCB")
    pollutants = models.JSONField(default=dict, blank=True)

    class Meta:
        ordering = ["-timestamp"]
        indexes = [models.Index(fields=["location", "-timestamp"], name="ground_loc_time_idx")]


class AQIGridPoint(models.Model):
    """Spatially gridded satellite/model AQI estimate used when no fresh station is nearby."""
    lat = models.FloatField()
    lon = models.FloatField()
    aqi = models.FloatField()
    timestamp = models.DateTimeField(db_index=True)
    source = models.CharField(max_length=40, default="satellite_model")
    model_version = models.CharField(max_length=80, blank=True)
    uncertainty_low = models.FloatField(null=True, blank=True)
    uncertainty_high = models.FloatField(null=True, blank=True)

    class Meta:
        indexes = [models.Index(fields=["timestamp"], name="aqi_grid_time_idx")]
