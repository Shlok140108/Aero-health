"""Connect alert evaluation to AeroHealth's existing XGBoost/Open-Meteo and forecast models.
Optional smoke/stagnation records are only used when real ingestion has populated them.
"""
import math
from datetime import timedelta
from django.apps import apps
from django.conf import settings
from django.utils import timezone


def distance_km(lat1, lon1, lat2, lon2):
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    dp, dl = math.radians(lat2-lat1), math.radians(lon2-lon1)
    a = math.sin(dp/2)**2 + math.cos(p1)*math.cos(p2)*math.sin(dl/2)**2
    return 2*r*math.asin(math.sqrt(a))

def _bbox(lat, lon, radius_km):
    lat_delta = radius_km / 110.574
    lon_delta = radius_km / (111.320 * max(0.1, math.cos(math.radians(lat))))
    return (max(-90, lat-lat_delta), min(90, lat+lat_delta),
            max(-180, lon-lon_delta), min(180, lon+lon_delta))

class Conditions:
    def __init__(self, lat, lon, now=None, cache=None):
        self.lat, self.lon = float(lat), float(lon)
        self.now = now or timezone.now()
        self.cache = cache if cache is not None else {}

    def _memo(self, key, fn):
        # 5 decimal places prevents accidental cross-user location reuse.
        k = (key, round(self.lat, 5), round(self.lon, 5))
        if k not in self.cache: self.cache[k] = fn()
        return self.cache[k]

    def aqi(self): return self._memo("aqi", self._load_aqi)

    def _load_aqi(self):
        GroundReading = apps.get_model("airquality", "GroundReading")
        Location = apps.get_model("airquality", "Location")
        Grid = apps.get_model("airquality", "AQIGridPoint")
        max_station_age = timedelta(hours=getattr(settings, "ALERTS_MAX_DATA_AGE_HOURS", 6))
        max_grid_age = timedelta(hours=getattr(settings, "ALERTS_GRID_MAX_AGE_HOURS", 12))
        stations=[]
        for loc in Location.objects.filter(is_cpcb_station=True).iterator():
            dist=distance_km(self.lat,self.lon,loc.lat,loc.lon)
            if dist <= 10: stations.append((dist,loc))
        # Search every eligible station, not only the nearest one: the closest may be stale.
        for dist,loc in sorted(stations,key=lambda item:item[0]):
            reading=GroundReading.objects.filter(location=loc,aqi__isnull=False,timestamp__gte=self.now-max_station_age,timestamp__lte=self.now).order_by("-timestamp").first()
            if reading:
                return {"value":float(reading.aqi),"source":"ground_sensor","place":loc.name,"distance_km":round(dist,1),
                        "timestamp":reading.timestamp,"model_version":"","uncertainty_low":None,"uncertainty_high":None}
        grids=[]
        min_lat,max_lat,min_lon,max_lon=_bbox(self.lat,self.lon,25)
        grid_qs=Grid.objects.filter(timestamp__gte=self.now-max_grid_age,timestamp__lte=self.now,
                                    lat__gte=min_lat,lat__lte=max_lat,lon__gte=min_lon,lon__lte=max_lon)
        for point in grid_qs.iterator():
            dist=distance_km(self.lat,self.lon,point.lat,point.lon)
            if dist <= 25: grids.append((dist,point))
        if grids:
            dist,point=min(grids,key=lambda item:(-item[1].timestamp.timestamp(),item[0]))
            return {"value":float(point.aqi),"source":point.source or "satellite_model","place":"nearby model grid","distance_km":round(dist,1),
                    "timestamp":point.timestamp,"model_version":point.model_version,"uncertainty_low":point.uncertainty_low,"uncertainty_high":point.uncertainty_high}
        # This project's current fallback is Open-Meteo pollutant data + its XGBoost AQI estimator.
        try:
            from dashboard.api import build
            payload = build(self.lat, self.lon)
            value = payload.get("aqi", {}).get("value")
            if value is None: return None
            return {"value": float(value), "source": "model_estimate", "place": "your saved location",
                    "timestamp": self.now, "model_version": "aqi_xgboost + Open-Meteo", "uncertainty_low":None,"uncertainty_high":None}
        except Exception:
            return None

    def forecast(self): return self._memo("forecast", self._load_forecast)

    def _load_forecast(self):
        Forecast = apps.get_model("weather", "AQIForecast")
        Location = apps.get_model("airquality", "Location")
        candidates = []
        for loc in Location.objects.all().iterator():
            d = distance_km(self.lat, self.lon, loc.lat, loc.lon)
            if d <= 100: candidates.append((d, loc))
        if candidates:
            loc = min(candidates, key=lambda x: x[0])[1]
            qs = Forecast.objects.filter(location=loc, forecast_for__gt=self.now,
                                         forecast_for__lte=self.now+timedelta(hours=72),
                                         generated_at__gte=self.now-timedelta(hours=getattr(settings, "ALERTS_FORECAST_MAX_AGE_HOURS", 24)))
            newest = qs.order_by("-generated_at").values_list("generated_at", flat=True).first()
            if newest:
                return [{"prediction": float(r.prediction), "forecast_for": r.forecast_for,
                         "hours": max(1, math.ceil((r.forecast_for-self.now).total_seconds()/3600)),
                         "place": loc.name, "model_version": r.model_version,
                         "data_timestamp": r.generated_at, "uncertainty_low": r.confidence_lower,
                         "uncertainty_high": r.confidence_upper}
                        for r in qs.filter(generated_at=newest).order_by("forecast_for")]
        # Fallback to the project's existing Open-Meteo + XGBoost daily AQI forecast.
        try:
            from dashboard.api import build_prediction
            payload = build_prediction(self.lat, self.lon)
            out = []
            for i, day in enumerate(payload.get("days", [])[:3]):
                value = day.get("aqi_max")
                if value is None: continue
                when = self.now + timedelta(hours=12 + (24 * i))
                out.append({"prediction": float(value), "forecast_for": when,
                            "hours": max(1, math.ceil((when-self.now).total_seconds()/3600)),
                            "place": "your saved location", "model_version": "aqi_xgboost + Open-Meteo daily estimate",
                            "data_timestamp": self.now})
            return out
        except Exception:
            return []

    def smoke(self, radius_km):
        def load():
            Model = apps.get_model("alerts", "SmokeDriftPrediction")
            cutoff = self.now - timedelta(hours=getattr(settings, "ALERTS_SMOKE_MAX_AGE_HOURS", 12))
            min_lat,max_lat,min_lon,max_lon=_bbox(self.lat,self.lon,radius_km)
            rows = Model.objects.filter(generated_at__gte=cutoff, predicted_for__gte=self.now,
                                        lat__gte=min_lat,lat__lte=max_lat,lon__gte=min_lon,lon__lte=max_lon)
            hits = [(distance_km(self.lat, self.lon, x.lat, x.lon), x) for x in rows]
            hits = [(d, x) for d, x in hits if d <= radius_km]
            if not hits: return None
            d, row = min(hits, key=lambda pair: pair[1].predicted_for)
            return {"hours": max(1, math.ceil((row.predicted_for-self.now).total_seconds()/3600)),
                    "distance_km": round(d, 1), "hotspot_count": row.hotspot_count,
                    "source": row.source, "timestamp": row.generated_at}
        return self._memo(("smoke", radius_km), load)

    def dispersion(self):
        def load():
            Model = apps.get_model("alerts", "WeatherReading")
            cutoff = self.now - timedelta(hours=getattr(settings, "ALERTS_WEATHER_MAX_AGE_HOURS", 3))
            min_lat,max_lat,min_lon,max_lon=_bbox(self.lat,self.lon,100)
            rows = Model.objects.filter(timestamp__gte=cutoff, timestamp__lte=self.now+timedelta(hours=1),
                                        lat__gte=min_lat,lat__lte=max_lat,lon__gte=min_lon,lon__lte=max_lon)
            near = [(distance_km(self.lat, self.lon, x.lat, x.lon), x) for x in rows]
            near = [(d, x) for d, x in near if d <= 100]
            if not near: return None
            d, row = min(near, key=lambda pair: pair[0])
            if row.wind_speed_ms is None or row.boundary_layer_m is None: return None
            vi = row.wind_speed_ms * row.boundary_layer_m
            return {"ventilation_index": vi, "poor": vi < getattr(settings, "ALERTS_VENTILATION_POOR_M2S", 6000),
                    "timestamp": row.timestamp, "distance_km": round(d, 1)}
        return self._memo("dispersion", load)
