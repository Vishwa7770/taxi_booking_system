"""
taxi_project/asgi.py
ASGI config – routes HTTP and WebSocket connections.
"""
import os
from django.core.asgi import get_asgi_application
from channels.routing import ProtocolTypeRouter, URLRouter
from channels.auth import AuthMiddlewareStack

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "taxi_project.settings")

django_asgi_app = get_asgi_application()

# Import routing AFTER django setup to avoid AppRegistryNotReady
from taxiapp import routing  # noqa: E402

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": AuthMiddlewareStack(
            URLRouter(routing.websocket_urlpatterns)
        ),
    }
)
