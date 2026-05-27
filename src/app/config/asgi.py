import os

import django

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "app.config.settings.prod")

from app.config.logging import configure_logging

configure_logging()

django.setup()

from channels.routing import ProtocolTypeRouter, URLRouter  # noqa: E402
from channels.security.websocket import OriginValidator  # noqa: E402
from django.conf import settings  # noqa: E402
from django.core.asgi import get_asgi_application  # noqa: E402

from app.ws.middleware import JWTAuthMiddleware, RequestIdMiddleware  # noqa: E402
from app.ws.routing import websocket_urlpatterns  # noqa: E402

django_asgi_app = get_asgi_application()

application = ProtocolTypeRouter(
    {
        "http": django_asgi_app,
        "websocket": OriginValidator(
            RequestIdMiddleware(JWTAuthMiddleware(URLRouter(websocket_urlpatterns))),
            settings.WS_ALLOWED_ORIGINS,
        ),
    }
)
