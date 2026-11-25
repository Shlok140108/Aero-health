import csv
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from airquality.models import Location, GroundReading

class Command(BaseCommand):
    help = "Import station AQI CSV with station_name,lat,lon,aqi,timestamp and optional state/source/is_cpcb_station."
    def add_arguments(self, parser): parser.add_argument("csv_path")
    def handle(self,*args,**opts):
        count=0
        try:
            with open(opts["csv_path"],newline="",encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    lat,lon=float(row["lat"]),float(row["lon"])
                    if not (-90<=lat<=90 and -180<=lon<=180): raise ValueError("Station coordinates out of range")
                    name=row["station_name"].strip()
                    loc,_=Location.objects.get_or_create(name=name,lat=lat,lon=lon,defaults={"state":row.get("state", ""),"is_cpcb_station":row.get("is_cpcb_station","true").lower() in ("1","true","yes")})
                    dt=datetime.fromisoformat(row["timestamp"].replace("Z","+00:00")); dt=timezone.make_aware(dt) if timezone.is_naive(dt) else dt
                    GroundReading.objects.create(location=loc,aqi=float(row["aqi"]),timestamp=dt,source=row.get("source") or "CPCB")
                    count+=1
        except (OSError,KeyError,ValueError) as exc: raise CommandError(str(exc))
        self.stdout.write(self.style.SUCCESS(f"Imported {count} ground-station readings."))
