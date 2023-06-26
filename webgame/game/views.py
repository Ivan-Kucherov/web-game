from django.shortcuts import render
from rest_framework.views import APIView
from django.contrib.auth import authenticate, login
from rest_framework.response import Response
from rest_framework import authentication, permissions,generics
from django.contrib.auth.models import User
from rest_framework import status
from rest_framework import viewsets
from rest_framework.pagination import PageNumberPagination
from rest_framework_simplejwt.authentication import JWTAuthentication
from django.conf import settings
from rest_framework_simplejwt.tokens import RefreshToken
import redis
import uuid
import numpy as np
from webgame.game.asgi import game
from webgame.game.models import Player
#from webgame.game import game
from webgame.game.serializers import LoginRequestSerializer, PlayerSerializer, UsersSerializer,RegisterRequestSerializer

redis_storage = redis.StrictRedis(host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=0)
def get_tokens_for_user(user):
    refresh = RefreshToken.for_user(user)

    return {
        'refresh': str(refresh),
        'access': str(refresh.access_token),
    }

class LargeResultsSetPagination(PageNumberPagination):
    page_size = 100
    page_size_query_param = 'page_size'
    max_page_size = 100

class StandardResultsSetPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = 'page_size'
    max_page_size = 20

class ListPlayers(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    queryset = Player.objects.all()
    serializer_class = PlayerSerializer
    pagination_class = StandardResultsSetPagination

class Player_(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request, *args, **kwargs):     
        try:
            # id = request.query_params["id"]
            name = self.kwargs["uname"]
            if name != None:
                print(name)
                u = User.objects.get(username=name)
                player_object = Player.objects.get(user=u)
                serializer = PlayerSerializer(player_object)
        except:
            pass

        return Response(serializer.data)
class User_(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request, *args, **kwargs):     
        try:
            user=request.user
            serializer = UsersSerializer(user)
        except:
            pass
        return Response(serializer.data)


    def get(self, request, format=None):
        """
        Return a list of all users.
        """
        usernames = [user.username for user in User.objects.all()]
        return Response(usernames)
'''
class GameBot(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticatedOrReadOnly]
    def post(self, request, format=None):
        #redis_storage.set('0',redis_storage.get('0') + 1)
        #redis_storage.lpush('1',1,2,3)
        
        if redis_storage.exists('b_'+request.user.id) == 1:
            return Response('was started',status=210)
        else:
            game_id = str(uuid.uuid1())
            redis_storage.set('b_'+request.user.id,game_id,ex=settings.GAME_TIME)
            field = np.zeros((8,8,3),int)
            field[2,5,0] = 1
            field[5,2,0] = -1
            redis_storage.rpush(game_id,'p',request.user.id,field.tobytes())
            redis_storage.expire(game_id,settings.GAME_TIME)
        return Response(status=status.HTTP_200_OK)
    def get(self, request, format=None):
        if redis_storage.exists('b_'+request.user.id) == 1:
            return Response('was started',status=210)
        else:
            game_id = str(uuid.uuid1())
            redis_storage.set('b_'+request.user.id,game_id,ex=settings.GAME_TIME)
            field = np.zeros((8,8,3),int)
            field[2,5,0] = 1
            field[5,2,0] = -1
            redis_storage.rpush(game_id,'p',request.user.id,field.tobytes())
            redis_storage.expire(game_id,settings.GAME_TIME)
        return Response(status=status.HTTP_200_OK)


class GamePlayer(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, format=None):
        if redis_storage.exists('wait') == 1:
            wait = redis_storage.lrange('wait', 0, -1)
            if request.user.id in wait:
                return Response('was started',status=210)
            else:
                game_id = str(uuid.uuid1())
                redis_storage.set(request.user.id,game_id,ex=settings.GAME_TIME)
                field = np.zeros((8,8,3),int)
                field[2,5,0] = 1
                field[5,2,0] = -1
                redis_storage.rpush(game_id,request.user.id,field.tobytes())
                redis_storage.expire(game_id,settings.GAME_TIME)
            return Response(status=status.HTTP_200_OK)
'''
#release {"username":"","password":""}->{"refresh": "","access": ""}
class LoginAPI(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request, format=None):
        serializer = LoginRequestSerializer(data=request.data)
        if serializer.is_valid():
            authenticated_user = authenticate(**serializer.validated_data)
            if authenticated_user is not None:
                return Response(get_tokens_for_user(authenticated_user),status=200)
            else:
                return Response({'error': 'Invalid credentials'}, status=403)
        else:
            return Response(serializer.errors, status=400)
#release {"username":"","email":"","password":"","password2":""}->{"refresh": "","access": ""}
class RegisterAPI(APIView):
    permission_classes = [permissions.AllowAny]
    def post(self, request, format=None):
        serializer = RegisterRequestSerializer(data=request.data)
        if serializer.is_valid():
            auth_user = authenticate(username=serializer.validated_data['username'],password=serializer.validated_data['password'])
            if auth_user is not None:
                return Response(get_tokens_for_user(auth_user), status=201)
            if User.objects.filter(username=serializer.validated_data['username']).exists():
                return Response("Name is in use",status=409)
            if serializer.validated_data['password'] == serializer.validated_data['password2']:
                user = User.objects.create_user(username=serializer.validated_data['username'],
                                    email=serializer.validated_data['email'],
                                    password=serializer.validated_data['password'])
                player = Player()
                player.user = user
                player.save()
                return Response(get_tokens_for_user(user), status=200)
        else:
            print(serializer.errors)
            return Response(serializer.errors, status=400)
#release -H "Authorization: Bearer ..."->username
class Atest(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request, format=None):
        return Response(request.user.username,status=200)
class MoveBot(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    def post(self, request, format=None):
        print(np.array(request.data))
        return Response(request.user.username,status=200)

class CreateGame(APIView):
    authentication_classes = [JWTAuthentication]
    permission_classes = [permissions.IsAuthenticated]
    def get(self, request, format=None):
        if redis_storage.exists('b_'+str(request.user.id)) == 1:
            map=np.frombuffer(redis_storage.get('b_'+str(request.user.id)),dtype=type(True)).reshape((16,16,4))
            print(map)
            g = game.Game(map=map)
            return Response({'map':g.map,
                             'player0':g.player0pos,
                             'player1':g.player1pos})
        else:
            g = game.Game()
            redis_storage.set('b_'+str(request.user.id),g.map.tobytes())
            return Response({'map':g.map,
                    'player0':g.player0pos,
                    'player1':g.player1pos})
