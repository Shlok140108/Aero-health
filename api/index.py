import os
import sys
from pathlib import Path

# Make the project root importable
sys.path.append(str(Path(__file__).resolve().parent.parent))

# CHANGE "config" to the folder that contains your settings.py
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "aerohealth.settings")

from django.core.wsgi import get_wsgi_application  # noqa: E402

app = get_wsgi_application()
