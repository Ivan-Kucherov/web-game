# Встроенные импорты.

# from my_proj.game.models import Game
# from my_proj.game.utils import get_live_score_for_gameclass

import asyncio
import datetime
import json
import time
import uuid
import nest_asyncio
from channels.generic.websocket import AsyncWebsocketConsumer
from channels.auth import login
from django.conf import settings
from django.contrib.auth import get_user_model
from django.forms import ValidationError
import numpy as np
import redis
from rest_framework_simplejwt.tokens import AccessToken
from django.contrib.auth.models import User
from channels.db import database_sync_to_async
from rest_framework_simplejwt.tokens import TokenError
from threading import Timer


from webgame.game.asgi.game import Game, Memory
from webgame.game.models import Game as Games, Player


class GameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.user = None
        self.Spect = True
        self.isOne = False
        self.memory = Memory()
        self.room_name = self.scope["url_route"]["kwargs"]["game_id"]
        #print("--", self.scope["url_route"]["kwargs"])
        self.game = self.memory.GetGame(self.room_name)
        self.Game = None
        if self.game is not None:
            self.Player0 = self.game[0]
            self.Player1 = self.game[1]
            self.move_ = self.game[5]
            self.room_group_name = "game_%s" % self.room_name
            await self.channel_layer.group_add(self.room_group_name, self.channel_name)
            await self.accept()

        else:
            pass

    @database_sync_to_async
    def get_name(self, id):
        return User.objects.get(id=id)

    @database_sync_to_async
    def save_win(self, win):
        u0 = User.objects.get(username=self.Player0)
        u1 = User.objects.get(username=self.Player1)
        p0 = Player.objects.get(user=u0)
        p1 = Player.objects.get(user=u1)
        game = Games()
        game.player0 = p0
        game.player1 = p1
        game.map = self.Game.map.tobytes()
        p0.all = p0.all + 1
        p1.all = p1.all + 1
        if win == self.Player0:
            p0.wins = p0.wins + 1
            game.win = p0
        elif win == self.Player1:
            p1.wins = p1.wins + 1
            game.win = p1
        else:
            game.win = None
        game.save()
        p0.save()
        p1.save()

    @database_sync_to_async
    def get_player(self, user_):
        return Player.objects.get(user=user_)

    @database_sync_to_async
    def save_player(self, user_):
        return Player.objects.get(user=user_)

    async def disconnect(self, close_code):
        # Leave room group
        # if self.game is not None:
        #    self.memory.SaveGame(self.room_name,self.game)
        await self.channel_layer.group_discard(self.room_group_name, self.channel_name)

    # Receive message from WebSocket
    async def receive(self, text_data):

        text_data_json = json.loads(text_data)
        if text_data_json["_type"] == "token":  # Авторизация пользователя
            try:
                user = text_data_json["token"]
                access_token_obj = AccessToken(user)
                user_id = access_token_obj['user_id']
                self.user = str(await self.get_name(user_id))
                if self.Player0 == self.user:
                    self.Spect = False
                    self.isOne = True
                elif self.Player1 == self.user:
                    self.Spect = False
                    self.isOne = False
                self.Game = Game(
                    self.game[2], self.game[3], self.game[4], self.isOne)
                self.move = True if self.game[5] == self.user else False
                print("--", self.game[5], self.user)
                await self.send("access")
                await self.send(json.dumps({'_type': "data",
                                            'map': self.Game.map.tolist(),
                                            'player0': self.Game.player0pos.tolist(),
                                            'player1': self.Game.player1pos.tolist(),
                                            "user0": self.Player0,
                                            "user1": self.Player1,
                                            "move": self.game[5],
                                            'score': self.Game.score}))
                print("Game auth", self.user)
            except TokenError:
                await self.send("Invalid Token")

        # if  self.scope["user"]
        if not (self.Spect) and self.move:
            if text_data_json["_type"] == "move":
                print("move", text_data_json["pos"])
                # self.Game = Game(self.game[2], self.game[3], self.game[4], self.isOne)
                pos = np.fromstring(
                    text_data_json["pos"], sep=',', dtype=int).tolist()
                r = self.Game.move(pos)
                if type(r) != type(ValueError()):
                    if r == 0:
                        await self.channel_layer.group_send(
                            self.room_group_name, {
                                "type": "changed",
                                'map': self.Game.map.tolist(),
                                'player0': self.Game.player0pos.tolist(),
                                'player1': self.Game.player1pos.tolist(),
                                "user0": self.Player0,
                                "user1": self.Player1,
                                'move': self.move_,
                                'score': self.Game.score}
                        )
                    else:
                        if r == 201:
                            await self.channel_layer.group_send(
                                self.room_group_name, {
                                    "type": "End",
                                    'map': self.Game.map.tolist(),
                                    'player0': self.Game.player0pos.tolist(),
                                    'player1': self.Game.player1pos.tolist(),
                                    "user0": self.Player0,
                                    "user1": self.Player1,
                                    "win": self.Player0}
                            )
                            win = self.Player0
                        elif r == 202:
                            await self.channel_layer.group_send(
                                self.room_group_name, {
                                    "type": "End",
                                    'map': self.Game.map.tolist(),
                                    'player0': self.Game.player0pos.tolist(),
                                    'player1': self.Game.player1pos.tolist(),
                                    "user0": self.Player0,
                                    "user1": self.Player1,
                                    "win": self.Player1}
                            )
                            win = self.Player1
                        elif r == 203:
                            await self.channel_layer.group_send(
                                self.room_group_name, {
                                    "type": "End",
                                    'map': self.Game.map.tolist(),
                                    'player0': self.Game.player0pos.tolist(),
                                    'player1': self.Game.player1pos.tolist(),
                                    "user0": self.Player0,
                                    "user1": self.Player1,
                                    "win": "-"}
                            )
                            win = None
                        await self.save_win(win)
                else:
                    await self.send(json.dumps({'_type': "badMove",
                                                'map': self.Game.map.tolist(),
                                                'player0': self.Game.player0pos.tolist(),
                                                'player1': self.Game.player1pos.tolist()}))
            if text_data_json["_type"] == "draw":
                # self.Game = Game(self.game[2], self.game[3], self.game[4], self.isOne)
                points = np.array(json.loads(text_data_json["points"]))
                r = self.Game.draw(points)
                if r == 1:
                    await self.channel_layer.group_send(
                        self.room_group_name, {
                            "type": "changed",
                            'map': self.Game.map.tolist(),
                            'player0': self.Game.player0pos.tolist(),
                            'player1': self.Game.player1pos.tolist(),
                            "user0": self.Player0,
                            "user1": self.Player1,
                            "move": self.move_,
                            'score': self.Game.score}
                    )
                else:
                    if r == -1:
                        await self.send(json.dumps({'_type': "badDraw",
                                                    'map': self.Game.map.tolist(),
                                                    'player0': self.Game.player0pos.tolist(),
                                                    'player1': self.Game.player1pos.tolist()}))
                    else:
                        if r == 201:
                            await self.channel_layer.group_send(
                                self.room_group_name, {
                                    "type": "End",
                                    'map': self.Game.map.tolist(),
                                    'player0': self.Game.player0pos.tolist(),
                                    'player1': self.Game.player1pos.tolist(),
                                    "user0": self.Player0,
                                    "user1": self.Player1,
                                    "win": self.Player0}
                            )
                            win = self.Player0
                        elif r == 202:
                            await self.channel_layer.group_send(
                                self.room_group_name, {
                                    "type": "End",
                                    'map': self.Game.map.tolist(),
                                    'player0': self.Game.player0pos.tolist(),
                                    'player1': self.Game.player1pos.tolist(),
                                    "user0": self.Player0,
                                    "user1": self.Player1,
                                    "win": self.Player1}
                            )
                            win = self.Player1
                        elif r == 203:
                            await self.channel_layer.group_send(
                                self.room_group_name, {
                                    "type": "End",
                                    'map': self.Game.map.tolist(),
                                    'player0': self.Game.player0pos.tolist(),
                                    'player1': self.Game.player1pos.tolist(),
                                    "user0": self.Player0,
                                    "user1": self.Player1,
                                    "win": "-"}
                            )
                            win = None
                        await self.save_win(win)
                        # self.Game.move()
        else:
            await self.send(json.dumps({'_type': "badMove",
                                        'map': self.Game.map.tolist(),
                                        'player0': self.Game.player0pos.tolist(),
                                        'player1': self.Game.player1pos.tolist()}))
        if text_data_json["_type"] == "data":
            if self.Game is not None:
                await self.send(json.dumps({'_type': "data",
                                            'map': self.Game.map.tolist(),
                                            'player0': self.Game.player0pos.tolist(),
                                            'player1': self.Game.player1pos.tolist(),
                                            "user0": self.Player0,
                                            "user1": self.Player1,
                                            "move": self.game[5],
                                            'score': self.Game.score}))
            else:
                self.send(json.dumps({'_type': "data",
                                      'map': self.game[2],
                                      'player0': self.game[3],
                                      'player1': self.game[4],
                                      "user0": self.Player0,
                                      "user1": self.Player1,
                                      "move": self.game[5],
                                      'score': self.Game.score}))
        if text_data_json["_type"] == "player":
            # print(self.game[2])
            if self.Spect:
                await self.send(json.dumps({'_type': "spect",
                                            'map': self.Game.map.tolist(),
                                            'player0': self.Game.player0pos.tolist(),
                                            'player1': self.Game.player1pos.tolist(),
                                            "user0": self.Player0,
                                            "user1": self.Player1,
                                            'score': self.Game.score}))
            else:
                await self.send(json.dumps({'_type': "player",
                                            'map': self.Game.map.tolist(),
                                            'player0': self.Game.player0pos.tolist(),
                                            'player1': self.Game.player1pos.tolist(),
                                            "user0": self.Player0,
                                            "user1": self.Player1,
                                            "isOne": self.isOne,
                                            "move": self.move,
                                            'score': self.Game.score}))
        # self.memory.SaveGame(self.room_name, self.Game,
        #                     self.Player0, self.Player1)

    # Receive message from room group
    async def End(self, event):
        self.Game.map = np.asarray(event["map"], dtype=np.bool_)
        self.Game.player0pos = event["player0"]
        self.Game.player1pos = event["player1"]
        self.win = event["win"]
        # self.memory.SaveGame(self.room_name, self.Game,
        #                     self.Player0, self.Player1)
        await self.send(json.dumps({'_type': "End",
                                    'map': self.Game.map.tolist(),
                                    'player0': self.Game.player0pos.tolist(),
                                    'player1': self.Game.player1pos.tolist(),
                                    'win': event["win"],
                                    'score': self.Game.score}))

    async def changed(self, event):
        if self.Player0 == event["move"]:
            self.move_ = self.Player1
        else:
            self.move_ = self.Player0
        self.Game.map = np.asarray(event["map"], dtype=np.bool_)
        self.Game.player0pos = event["player0"]
        self.Game.player1pos = event["player1"]
        self.Game.score = event["score"]
        self.memory.SaveGame(self.room_name, self.Game,
                             self.Player0, self.Player1, self.move_)
        self.move = False if self.Spect else not (self.move)
        await self.send(json.dumps({'_type': "moved",
                                    'map': self.Game.map.tolist(),
                                    'player0': self.Game.player0pos.tolist(),
                                    'player1': self.Game.player1pos.tolist(),
                                    'move': self.move_,
                                    'score': self.Game.score}))


class FindGameConsumer(AsyncWebsocketConsumer):
    async def connect(self):
        self.confirm_time = None
        self.confirming = False
        self.wait = False
        # self.room_group_name = "user_%s" % self.user
        # await self.channel_layer.group_add(self.room_group_name, self.channel_name)
        self.redis_storage = redis.StrictRedis(
            host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=1)
        await self.accept()

    @ database_sync_to_async
    def get_name(self, id):
        return User.objects.get(id=id)

    async def disconnect(self, close_code):
        if self.confirm_time is not None:
            if (time.time() - self.confirm_time) > 25:
                await self.channel_layer.group_send("user_%s" % self.player1, {
                    "type": "go.next"
                })
                self.redis_storage.set("ban_%s" % self.user, "-", ex=300)
                await self.send(json.dumps({"_type": "ban", "time": "300"}))
                print("ban", self.user)
        # Leave room group
        if self.wait:
            self.redis_storage.zrem("Wait", self.user)
        try:
            await self.channel_layer.group_discard(self.room_group_name, self.channel_name)
        except AttributeError:
            pass
        # self.send(close_code)

    # Receive message from WebSocket
    async def receive(self, text_data):
        if self.confirm_time is not None:
            if (time.time() - self.confirm_time) > 25:
                await self.channel_layer.group_send("user_%s" % self.player1, {
                    "type": "go.next"
                })
                self.confirm_time = None
                self.redis_storage.set("ban_%s" % self.user, "-", ex=300)
                await self.send(json.dumps({"_type": "ban", "time": "300"}))
                print("ban", self.user)
        text_data_json = json.loads(text_data)
        if text_data_json["_type"] == "token":  # Авторизация пользователя
            try:
                user = text_data_json["token"]
                access_token_obj = AccessToken(user)
                user_id = access_token_obj['user_id']
                self.user = str(await self.get_name(user_id))
                self.room_group_name = "user_%s" % self.user
                await self.channel_layer.group_add(self.room_group_name, self.channel_name)
                await self.send("access")
                if self.wait:
                    self.redis_storage.zrem("Wait", self.user)
                print("auth", self.user)
            except TokenError:
                await self.send("Invalid Token")
            # print(self.user)
        if text_data_json["_type"] == "start":  # Поиск игрока
            await self.go_next("")
            """ban = self.redis_storage.execute_command(
                "EXPIRETIME ban_%s" % self.user) - time.time()
            if ban >= 0:
                self.send(json.dumps({"_type": "ban", "time": str(ban)}))
            else:
                players = self.redis_storage.zrevrange(
                    "Wait", 0, 1) # первые два ожидающие
                for player in players:
                    player = player.decode()
                    if (not (self.user == player)):
                        self.confirming = True
                        self.code = str(uuid.uuid4())
                        self.redis_storage.set(
                            "c_%s" % self.code, player, ex=20)
                        print("start game", self.code, player, self.user)
                        self.player0 = player
                        # self.player1 = self.user
                        self.send("confirming")
                        await self.channel_layer.group_send("user_%s" % player, {
                            "type": "confirm",
                            "code": self.code,
                            "player": self.user
                            })
                        break
                if (not (self.confirming)):
                    self.redis_storage.zadd("Wait", {self.user: time.time()})
                    self.player0 = self.user
                    print("start waiting ", self.user)
                    self.wait = True
            if text_data_json["_type"] == "confirm":
            self.code = text_data_json["code"]
            user2 = self.redis_storage.get("c_%s"%self.code)
            if user2 is not None:
                user2 = str(user2)
                if user2 == self.user:
                    await self.channel_layer.group_send(
                    "user_%s" % user2, {"type": "confirmed", "code": self.code}
                    )
                    self.player0 = self.user
                    self.player1 = user
                    await self.send("confirmed")
            else:
                self.redis_storage.set("ban_%s" % self.user, ex=300)
                await self.send("Time over")"""
        if text_data_json["_type"] == "confirmed":
            user2 = self.redis_storage.get("c_%s" % self.code)
            if user2 is not None:
                user2 = user2.decode()
                if user2 == self.user:
                    self.redis_storage.zrem("Wait", self.user)
                    self.wait = False
                    await self.channel_layer.group_send(
                        "user_%s" % self.player1, {
                            "type": "confirmed", "code": self.code}
                    )
                    self.player0 = self.user
                    await self.send(json.dumps({"_type": "created", "code": self.code}))
                    print("confirmed game", self.code, self.user, user2)
            else:
                if self.wait:
                    self.redis_storage.zrem("Wait", self.user)
                self.redis_storage.set("ban_%s" % self.user, "-", ex=300)
                await self.send(json.dumps({"_type": "ban", "time": "300"}))
                print("ban", self.user)

    # Receive message from room group

    async def chat_message(self, event):
        print(event)
        print(self.user)
        message = event["message"]

        # Send message to WebSocket
        await self.send(text_data=json.dumps({"message": message}))

    async def confirm(self, event):
        if self.wait:
            self.code = event["code"]
            self.player1 = event["player"]
            self.confirm_time = time.time()
            await self.send(json.dumps({"_type": "confirmed", "code": event["code"]}))
            print("confirm message", self.code, self.user)

    async def confirmed(self, event):
        self.player0 = self.redis_storage.get("c_%s" % self.code).decode()
        self.player1 = self.user
        # try:
        m = Memory(self.redis_storage)
        m.CreateGame(self.player0, self.player1, self.code)
        print(type(self.player0), type(self.code))
        self.redis_storage.rpush("g_%s" % self.player0, self.code)
        self.redis_storage.rpush("g_%s" % self.player1, self.code)
        self.redis_storage.rpush("games", self.code)
        self.redis_storage.expire("g_%s" % self.player0, 14400)
        self.redis_storage.expire("g_%s" % self.player1, 14400)
        if self.wait:
            self.redis_storage.zrem("Wait", self.user)
            self.wait = False
        await self.send(json.dumps({"_type": "created", "code": self.code}))
        print("created game", self.code, self.user)
        # except Exception as e:
        #    print(e.message)
        #    await self.send("Error")

    async def go_next(self, event):
        self.confirming = False
        ban = int(self.redis_storage.execute_command(
            "EXPIRETIME ban_%s" % self.user) - time.time())
        if ban >= 0:
            await self.send(json.dumps({"_type": "ban", "time": ban}))
        else:
            players = self.redis_storage.zrevrange(
                "Wait", 0, 1)  # первые два ожидающие
            for player in players:
                player = player.decode()
                if (not (self.user == player)):
                    self.confirming = True
                    self.code = str(uuid.uuid4())
                    self.redis_storage.set(
                        "c_%s" % self.code, player, ex=20)
                    print("start game", self.code, player, self.user)
                    self.player0 = player
                    # self.player1 = self.user
                    self.send("confirming")
                    await self.channel_layer.group_send("user_%s" % player, {
                        "type": "confirm",
                        "code": self.code,
                        "player": self.user
                    })
                    break
            if (not (self.confirming)):
                self.redis_storage.zadd("Wait", {self.user: time.time()})
                self.player0 = self.user
                print("start waiting ", self.user)
                self.wait = True



