import csv
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from alerts.models import WeatherReading

class Command(BaseCommand):
    help = "Import meteorological rows (lat,lon,timestamp,wind_speed_ms,boundary_layer_m,source)."
    def add_arguments(self, parser): parser.add_argument("csv_path")
    def handle(self,*args,**opts):
        count=0
        try:
            with open(opts["csv_path"],newline="",encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    dt=datetime.fromisoformat(row["timestamp"].replace("Z","+00:00")); dt=timezone.make_aware(dt) if timezone.is_naive(dt) else dt
                    WeatherReading.objects.create(lat=float(row["lat"]),lon=float(row["lon"]),timestamp=dt,wind_speed_ms=float(row["wind_speed_ms"]) if row.get("wind_speed_ms") else None,boundary_layer_m=float(row["boundary_layer_m"]) if row.get("boundary_layer_m") else None,source=row.get("source") or "")
                    count+=1
        except (OSError,KeyError,ValueError) as exc: raise CommandError(str(exc))
        self.stdout.write(self.style.SUCCESS(f"Imported {count} meteorological rows."))
