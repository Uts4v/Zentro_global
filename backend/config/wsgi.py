"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os
import time

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()

# Auto-run migrations on startup (Render free tier has no shell access)
from django.core.management import call_command
for attempt in range(3):
    try:
        call_command("migrate", "--verbosity", "0")
        break
    except Exception:
        if attempt < 2:
            time.sleep(3)
        continue
