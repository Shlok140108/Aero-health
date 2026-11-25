import csv
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from airquality.models import AQIGridPoint

class Command(BaseCommand):
    help = "Import calibrated satellite/model grid CSV with lat,lon,aqi,timestamp and optional source/model_version/uncertainty bounds."
    def add_arguments(self, parser): parser.add_argument("csv_path")
    def handle(self,*args,**opts):
        count=0
        try:
            with open(opts["csv_path"],newline="",encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    lat,lon=float(row["lat"]),float(row["lon"])
                    if not (-90<=lat<=90 and -180<=lon<=180): raise ValueError("Grid coordinates out of range")
                    dt=datetime.fromisoformat(row["timestamp"].replace("Z","+00:00")); dt=timezone.make_aware(dt) if timezone.is_naive(dt) else dt
                    opt=lambda key: float(row[key]) if row.get(key) not in (None,"") else None
                    AQIGridPoint.objects.create(lat=lat,lon=lon,aqi=float(row["aqi"]),timestamp=dt,source=row.get("source") or "satellite_model",model_version=row.get("model_version") or "",uncertainty_low=opt("uncertainty_low"),uncertainty_high=opt("uncertainty_high"))
                    count+=1
        except (OSError,KeyError,ValueError) as exc: raise CommandError(str(exc))
        self.stdout.write(self.style.SUCCESS(f"Imported {count} gridded AQI estimates."))
