from django.urls import path, re_path
from channels.routing import ProtocolTypeRouter, URLRouter
from .consumers import FindGameConsumer, GameConsumer

websockets = [
    re_path(
        r"^ws/find$", FindGameConsumer.as_asgi(),
        name="live-score",
    ),
    re_path(
        r"^ws/game/(?P<game_id>[A-Za-z0-9/-]+)$", GameConsumer.as_asgi(),
        name="game",
    ),
]
