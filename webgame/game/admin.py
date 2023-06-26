from django.contrib import admin

from webgame.game.models import Game, Player

# Register your models here.
admin.site.register(Player)
admin.site.register(Game)