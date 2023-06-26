from django.db import models
from django.contrib.auth.models import User
# Create your models here.
class Player(models.Model):
    user = models.OneToOneField(User, on_delete=models.CASCADE)
    wins = models.IntegerField(default=0)
    all = models.IntegerField(default=0)
    def __str__(self):
        return self.user.username
class Game(models.Model):
    player0 = models.ForeignKey(Player, on_delete=models.SET_NULL,null=True,related_name='Fisrt')
    player1 = models.ForeignKey(Player, on_delete=models.SET_NULL,null=True,related_name='Second')
    map = models.BinaryField(null=True)
    win = models.ForeignKey(Player, on_delete=models.SET_NULL,null=True,related_name='Win')
    def __str__(self):
        return self.pk
#class Results