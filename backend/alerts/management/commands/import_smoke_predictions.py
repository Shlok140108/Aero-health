import csv
from datetime import datetime
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from alerts.models import SmokeDriftPrediction

class Command(BaseCommand):
    help = "Import plume-model output CSV (lat,lon,predicted_for,generated_at,hotspot_count,total_frp)."
    def add_arguments(self, parser): parser.add_argument("csv_path")
    def handle(self,*args,**opts):
        count=0
        try:
            with open(opts["csv_path"],newline="",encoding="utf-8") as f:
                for row in csv.DictReader(f):
                    def dt(v):
                        x=datetime.fromisoformat(v.replace("Z","+00:00")); return timezone.make_aware(x) if timezone.is_naive(x) else x
                    SmokeDriftPrediction.objects.create(lat=float(row["lat"]),lon=float(row["lon"]),predicted_for=dt(row["predicted_for"]),generated_at=dt(row["generated_at"]),hotspot_count=int(row.get("hotspot_count") or 1),total_frp=float(row.get("total_frp") or 0),source=row.get("source") or "NASA FIRMS",model_version=row.get("model_version") or "")
                    count+=1
        except (OSError,KeyError,ValueError) as exc: raise CommandError(str(exc))
        self.stdout.write(self.style.SUCCESS(f"Imported {count} smoke-drift prediction rows."))
