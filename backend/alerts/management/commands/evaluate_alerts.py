from django.core.management.base import BaseCommand
from alerts.runner import evaluate_profiles

class Command(BaseCommand):
    help = "Evaluate opted-in AeroHealth profiles and create/send alerts."
    def add_arguments(self, parser):
        parser.add_argument("--send", action="store_true", help="Actually deliver notifications; default is dry-run.")
    def handle(self,*args,**opts):
        result=evaluate_profiles(dry_run=not opts["send"])
        self.stdout.write(self.style.SUCCESS(str(result)))
