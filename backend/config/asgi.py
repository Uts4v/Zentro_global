# config/asgi.py
import os

# This MUST be the very first line before any Django imports
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings")

# Django setup must happen before any app imports
import django
django.setup()

from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from notifications.middleware import JWTAuthMiddleware
from notifications.routing import websocket_urlpatterns

application = ProtocolTypeRouter({
    "http": get_asgi_application(),
    "websocket": JWTAuthMiddleware(
        URLRouter(websocket_urlpatterns)
    ),
})