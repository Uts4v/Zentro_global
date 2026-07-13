"""
WSGI config for config project.

It exposes the WSGI callable as a module-level variable named ``application``.

For more information on this file, see
https://docs.djangoproject.com/en/6.0/howto/deployment/wsgi/
"""

import os

from django.core.wsgi import get_wsgi_application

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'config.settings')

application = get_wsgi_application()

# Auto-run migrations on startup (needed for Render free tier with no shell access)
from django.core.management import call_command
try:
    call_command("migrate", "--verbosity", "0")
except Exception:
    pass
