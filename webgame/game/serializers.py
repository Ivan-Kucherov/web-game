from rest_framework import serializers
from django.contrib.auth.models import User

from webgame.game.models import Player


class UsersSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ('username', 'email', 'id')


class LoginRequestSerializer(serializers.Serializer):
    model = User
    username = serializers.CharField(required=True)
    password = serializers.CharField(required=True)


class RegisterRequestSerializer(serializers.Serializer):
    model = User
    username = serializers.CharField(required=True)
    email = serializers.CharField(required=True)
    password = serializers.CharField(required=True)
    password2 = serializers.CharField(required=True)


class PlayerSerializer(serializers.Serializer):
    model = Player
    all = serializers.IntegerField(required=True)
    wins = serializers.IntegerField(required=True)
    user = serializers.StringRelatedField(many=False)

# class MoveSerializer(serializers.Serializer):
   # st = serializers.ListField(child=serializers.IntegerField())
   # end = serializers.ListField(child=serializers.IntegerField())
   # user  = self.context.get("request").user
