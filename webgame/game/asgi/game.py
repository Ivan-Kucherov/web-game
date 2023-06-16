import time
import uuid
import numpy as np
from numba import njit
import numpy as np
import redis
from django.conf import settings


class Find:
    def __init__(self):
        self.redis_storage = redis.StrictRedis(
            host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=1)

    def Find(self, user, confirm):
        players = self.redis_storage.zrevrange("Wait", 0, 1)
        for player in players:
            if (not (user == str(player))):
                confirmed = confirm(user)
                if confirmed:
                    game = str(uuid.uuid4())
                    self.redis_storage.sadd("Games", uuid.uuid4())
                    return uuid.uuid4()
                else:
                    self.redis_storage.zrem("Wait", player)

        self.redis_storage.zadd("Wait", (user, time.time()))
        return None


class Memory:
    def __init__(self, redis_storage=None):
        self.redis_storage = redis.StrictRedis(
            host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=1) if redis_storage is None else redis_storage

    def CreateGame(self, user0, user1, room):
        print(room)
        print(self.redis_storage.exists(room))
        self.user0 = user0
        self.user1 = user1
        if self.redis_storage.exists(room) == 1:
            temp = self.redis_storage.lrange(room, 0, 4)
            map = np.frombuffer(temp[2], dtype=np.bool_).reshape((16, 16, 5))
            return map
        else:
            g = Game()
            self.redis_storage.rpush(
                room, *[user0, user1, g.map.tobytes(), g.player0pos.tobytes(), g.player1pos.tobytes()])
            self.redis_storage.expire(room, 14400)

    def GetGame(self, room):
        print(room)
        if self.redis_storage.exists(room) == 1:
            temp = self.redis_storage.lrange(room, 0, 4)
            self.user0 = temp[0].decode()
            self.user1 = temp[1].decode()
            map = np.frombuffer(temp[2], dtype=np.bool_).reshape(
                (16, 16, 5)).tolist()
            p0 = np.frombuffer(temp[3], dtype=int).tolist()
            p1 = np.frombuffer(temp[4], dtype=int).tolist()
            return [self.user0, self.user1, map, p0, p1]
        else:
            return None

    def SaveGame(self, room, game, u0=None, u1=None):
        self.redis_storage.delete(room)
        if (u0 is not None) and (u1 is not None):
            self.user0 = u0
            self.user1 = u1
        if type(game) == type([]):
            self.redis_storage.rpush(room, *game)
        if type(game) == type(Game):
            self.redis_storage.rpush(room, [self.user0, self.user1, game.map.tobytes(
            ), game.player0pos.tobytes(), game.player1pos.tobytes()])
        # if

    def MoveGame(self, obj, room, user):
        if self.redis_storage.exists(room) == 1:
            temp = self.redis_storage.lpop(room, 4)
            map = np.frombuffer(temp[2], dtype=np.bool_).reshape(
                (16, 16, 5)).tolist()
            p0 = np.frombuffer(temp[3], dtype=np.bool_).tolist()
            p1 = np.frombuffer(temp[4], dtype=np.bool_).tolist()
            if (user == temp[0].decode()):
                game = Game(map, p0, p1)
            else:
                game = Game(map, p0, p1, False)
            game.move(obj)
            self.redis_storage.rpush(
                room, *[temp[0], temp[1], game.map.tobytes(), game.player0pos.tobytes(), game.player1pos.tobytes()])
            return game.map
        else:
            return None

    def MoveGameMap(self, room, user, obj):
        if self.redis_storage.exists(room) == 1:
            temp = self.redis_storage.lpop(room, 4)
            map = np.frombuffer(temp[2], dtype=np.bool_).reshape((16, 16, 5))
            p0 = np.frombuffer(temp[3], dtype=np.bool_)
            p1 = np.frombuffer(temp[4], dtype=np.bool_)
            if (user == temp[0].decode()):
                game = Game(map, p0, p1)
            else:
                game = Game(map, p0, p1, False)
            game.move(obj)
            self.redis_storage.rpush(
                room, *[temp[0], temp[1], game.map.tobytes(), game.player0pos.tobytes(), game.player1pos.tobytes()])
            return game.map
        else:
            return None


class Game:
    def __init__(self, map=None, player0=None, player1=None, playOne=True):
        if map is None:
            self.player0 = playOne
            self.map = np.zeros((16, 16, 5), dtype=np.bool_)
            self.map[6, 9, 0] = True
            self.map[6, 9, 2] = True
            self.map[9, 6, 1] = True
            self.map[9, 6, 3] = True
            self.player0pos = np.array([6, 9])
            self.player1pos = np.array([9, 6])
        else:
            if player0 is not None:
                self.player0 = playOne
                self.map = np.asarray(map, dtype=np.bool_)
                self.player0pos = player0
                self.player1pos = player1
            else:
                self.player0 = playOne
                self.map = np.asarray(map, dtype=np.bool_)
                self.player0pos = np.where(self.map[:, :, 0])
                self.player1pos = np.where(self.map[:, :, 1])

    def __left(self, position, vec):
        # слева закрашено
        if vec[1] > 0:
            left = [position[0]+1, position[1]]
        if vec[1] < 0:
            left = [position[0]-1, position[1]]
        if vec[0] > 0:
            left = [position[0], position[1]+1]
        if vec[0] < 0:
            left = [position[0], position[1]+1]

    def __findrec(self, position, vec, void, state=True, player=2):
        # за пределы поля
        if position[0] > 15 or position[1] > 15 or position[0] < 0 or position[1] < 0:
            return None
        # закрашено другим игроком
        if player == 2:
            if self.map[position[0], position[1], 3]:
                return None
        else:
            if self.map[position[0], position[1], 2]:
                return None
        # закрасить замкнутую фигуру
        if position[0] == void[0] and position[1] == void[1]:
            return void
        # не закрашено
        if player == 2:
            if not (self.map[position[0], position[1], 2]):
                return None
        else:
            if not (self.map[position[0], position[1], 3]):
                return None
        # слева закрашено
        if vec[0] > 0 and state:
            if self.map[position[0], position[1]+1, player]:
                return self.__findrec([position[0], position[1]+1],
                                      [0, 1], void, state, player)

                return self.__findrec([position[0], position[1]+1],
                                      [-1, 1], void, False, player)

        elif vec[0] < 0 and state:
            if self.map[position[0], position[1]-1, player]:
                return self.__findrec([position[0], position[1]-1],
                                      [0, -1], void, state, player)

                return self.__findrec([position[0], position[1]-1],
                                      [1, -1], void, False, player)

        elif vec[1] > 0 and state:
            if self.map[position[0]-1, position[1], player]:
                return self.__findrec([position[0]-1, position[1]],
                                      [-1, 0], void, state, player)

                return self.__findrec([position[0]-1, position[1]],
                                      [-1, -1], void, False, player)

        elif vec[1] < 0 and state:
            if self.map[position[0]+1, position[1], player]:
                return self.__findrec([position[0]+1, position[1]],
                                      [1, 0], void, state, player)

                return self.__findrec([position[0]+1, position[1]],
                                      [1, 1], void, False, player)

        elif vec[0] > 0 and vec[1] > 0:
            if self.map[position[0]-1, position[1], player]:
                return self.__findrec([position[0]-1, position[1]],
                                      [-1, 0], void, state, player)

        elif vec[0] > 0 and vec[1] < 0:
            if self.map[position[0], position[1]+1, player]:
                return self.__findrec([position[0], position[1]+1],
                                      [0, 1], void, state, player)

        elif vec[0] < 0 and vec[1] > 0:
            if self.map[position[0], position[1]-1, player]:
                return self.__findrec([position[0], position[1]-1],
                                      [0, -1], void, state, player)

        elif vec[0] < 0 and vec[1] < 0:
            if self.map[position[0]+1, position[1], player]:
                return self.__findrec([position[0]+1, position[1]],
                                      [1, 0], void, state, player)

        return None

    def __find(self, position, player):
        if not (self.map[position[0]+1, position[1], player]):
            self.draw(self.__findrec([position[0]+1, position[1]+1], [
                      1, 1], [position[0]+1, position[1]], False, player), player)
            self.draw(self.__findrec([position[0]+1, position[1]-1], [
                      1, -1], [position[0]+1, position[1]], False, player), player)
            self.draw(self.__findrec([position[0], position[1]], [
                      0, -1], [position[0]+1, position[1]], False, player), player)
            self.draw(self.__findrec([position[0], position[1]], [0, 1], [
                      position[0]+1, position[1]], False, player), player)
        if not (self.map[position[0]-1, position[1], player]):
            self.draw(self.__findrec([position[0]-1, position[1]-1], [-1, -1], [
                      position[0]-1, position[1]], False, player), player)
            self.draw(self.__findrec([position[0]-1, position[1]+1], [-1, 1], [
                      position[0]-1, position[1]], False, player), player)
            self.draw(self.__findrec([position[0]+1, position[1]], [
                      1, 0], [position[0]-1, position[1]], False, player), player)
            self.draw(self.__findrec([position[0]-1, position[1]], [-1, 0], [
                      position[0]-1, position[1]], False, player), player)
        if not (self.map[position[0], position[1]+1, player]):
            self.draw(self.__findrec([position[0]+1, position[1]+1], [
                      1, 1], [position[0], position[1]+1], False, player), player)
            self.draw(self.__findrec([position[0]-1, position[1]+1], [-1, 1], [
                      position[0], position[1]+1], False, player), player)
            self.draw(self.__findrec([
                      position[0], position[1]], [-1, 0], [position[0], position[1]+1], False, player), player)
            self.draw(self.__findrec([position[0], position[1]], [1, 0], [
                      position[0], position[1]+1], False, player), player)
        if not (self.map[position[0], position[1]-1, player]):
            self.draw(self.__findrec([position[0]-1, position[1]-1], [-1, -1], [
                      position[0], position[1]-1], False, player), player)
            self.draw(self.__findrec([position[0]+1, position[1]-1], [
                      1, -1], [position[0], position[1]-1], False, player), player)
            self.draw(self.__findrec([position[0], position[1]], [1, 0], [
                      position[0], position[1]-1], False, player), player)
            self.draw(self.__findrec([
                      position[0], position[1]], [-1, 0], [position[0], position[1]-1], False, player), player)
        if not (self.map[position[0]+1, position[1]+1, player]):
            self.draw(self.__findrec([position[0]+1, position[1]], [1, 0], [
                      position[0]+1, position[1]+1], False, player), player)
            self.draw(self.__findrec([position[0], position[1]+1], [0, 1], [
                      position[0]+1, position[1]+1], False, player), player)
        if not (self.map[position[0]-1, position[1]-1, player]):
            self.draw(self.__findrec([position[0]-1, position[1]], [-1, 0], [
                      position[0]-1, position[1]-1], False, player), player)
            self.draw(self.__findrec([position[0], position[1]-1], [0, -1], [
                      position[0]-1, position[1]-1], False, player), player)
        if not (self.map[position[0]-1, position[1]+1, player]):
            self.draw(self.__findrec([position[0]-1, position[1]], [-1, 0], [
                      position[0]-1, position[1]+1], False, player), player)
            self.draw(self.__findrec([position[0], position[1]+1], [0, 1], [
                      position[0]-1, position[1]+1], False, player), player)
        if not (self.map[position[0]+1, position[1]-1, player]):
            self.draw(self.__findrec([position[0]+1, position[1]], [1, 0], [
                      position[0]+1, position[1]-1], False, player), player)
            self.draw(self.__findrec([position[0], position[1]-1], [0, -1], [
                      position[0]+1, position[1]-1], False, player), player)

        return True

    def __findvec(self, position, player, vec):
        if not (self.map[position[0]+1, position[1], player]):
            self.__findrec(position, vec, void, state=True, player=2)
    def drawold(self, position, player):
        print('draw', position)

        if (position is not None):
            print('draw', position)
            if (not (self.map[position[0], position[1], 4])):
                self.map[position[0], position[1], player] = True
                self.map[position[0], position[1], 4] = True
                if position[0] == 15 or position[1] == 15 or position[0] == 0 or position[1] == 0:
                    return None
                if not (self.map[position[0]+1, position[1], player]):
                    self.draw([position[0]+1, position[1]], player)
                else:
                    self.map[position[0]+1, position[1], 4] = True
                if not (self.map[position[0]-1, position[1], player]):
                    self.draw([position[0]-1, position[1]], player)
                else:
                    self.map[position[0]-1, position[1], 4] = True
                if not (self.map[position[0], position[1]+1, player]):
                    self.draw([position[0], position[1]+1], player)
                else:
                    self.map[position[0], position[1]+1, 4] = True
                if not (self.map[position[0], position[1]-1, player]):
                    self.draw([position[0], position[1]-1], player)
                else:
                    self.map[position[0], position[1]-1, 4] = True

    

    def __draw(self, list, player):
        for i in list:
            i.append(4)
            if self.map[tuple(i)]:
                continue
            else:
                self.map[tuple(i)] = True
                i[2] = player
                self.map[tuple(i)] = True
    def __check(self, list,player):
        self.c = []
        if len(list) != 3 and len(list) !=4:
            return False
        if len(list) == 3:
            l = None
            if list[0][0] == list[1][0]:
                print(1)
                if list[0][1] == list[2][1]:
                    rc = list[0]
                    l = [list[2],list[1]]
                    if rc[0] - list[1][0] < 0:
                        if rc[1] - list[2][1] < 0:
                            t = 4
                        if rc[1] - list[2][1] > 0:
                            t = 3
                    if rc[0] - list[1][0] > 0:
                        if rc[1] - list[2][1] < 0:
                            t = 2
                        if rc[1] - list[2][1] > 0:
                            t = 1
            if list[1][0] == list[2][0]:
                print(2)
                if list[1][1] == list[0][1]:
                    rc = list[1]
                    l = [list[2],list[0]]
                    if rc[0] - list[0][0] < 0:
                        if rc[1] - list[2][1] < 0:
                            t = 4
                        if rc[1] - list[2][1] > 0:
                            t = 3
                    if rc[0] - list[0][0] > 0:
                        if rc[1] - list[2][1] < 0:
                            t = 2
                        if rc[1] - list[2][1] > 0:
                            t = 1
            if  l is not None:
                dx = l[0][0] - l[1][0]
                dy = l[0][1] - l[1][1]
                
                sign_x = 1 if dx>0 else -1 if dx<0 else 0
                sign_y = 1 if dy>0 else -1 if dy<0 else 0
                
                if dx < 0: dx = -dx
                if dy < 0: dy = -dy
                
                if dx > dy:
                    pdx, pdy = sign_x, 0
                    es, el = dy, dx
                else:
                    pdx, pdy = 0, sign_y
                    es, el = dx, dy
                
                x, y = l[0][0], l[0][1]
                
                error, t = el/2, 0    
                print(rc,l,t)    
                self.map[x,rc[1],player] = True 
                self.map[x,rc[1],4] = True 
                self.map[x,y,player] = True 
                self.map[x,y,4] = True
                #self.c.append([x, y])
                #if not(self.map[x,rc[1],player]) or not(self.map[x,y,player]):
                #    return False
                #for i in range(rc[1],y+1):
                #    self.c.append([x, y])
                while t < el:
                    error -= es
                    if error < 0:
                        error += el
                        x += sign_x
                        y += sign_y
                    else:
                        x += pdx
                        y += pdy
                    t += 1
                    print(self.map[x,rc[1],player],self.map[x,y,player])
                    self.map[x,rc[1],player] = True 
                    self.map[x,rc[1],4] = True 
                    self.map[x,y,player] = True 
                    self.map[x,y,4] = True
                    #if not(self.map[x,rc[1],player]) or not(self.map[x,y,player]):
                    #    return False
                    #for i in range(rc[1],y+1):
                    #    self.c.append([x, y])
                return True
        if len(list) == 4:
            x1 = list[0][0]
            x2 = list[0][0]
            y1 = list[0][1]
            y2 = list[0][1]
            for i in list:
                x1 = i[0] if i[0]<x1 else x1
                x2 = i[0] if i[0]>x2 else x2
                y1 = i[1] if i[1]<y1 else y1
                y2 = i[1] if i[1]>y2 else y2
                print(i[0],i[1])
            print(x1,y1,x2,y2)
            for i in range(x1,x2+1):
                for j in range(y1,y2+1):
                    if i == x1 or i == x2 or j == y1 or j == y2:
                        if not(self.map[i,j,player]):
                            return False
                    self.c.append([i,j])

        return True

    def draw(self,list):
        if self.player0:
            player = 2
        else:
            player = 3
        if self.__check(list,player):
            self.__draw(self.c,player)
            if len(np.unique(np.logical_or(self.map[:, :, 2], self.map[:, :, 3]))) < 2:
                if np.count_nonzero(self.map[:, :, 2]) > np.count_nonzero(self.map[:, :, 3]):
                    return 201
                else:
                    return 202
            return 1
        else:
            return -1


    def move(self, obj):
        if self.player0:
            player = 2
        else:
            player = 3
        if np.shape(obj) != np.shape(self.map):
            if self.player0:
                if (((abs(obj[0]-self.player0pos[0]) > 1) or (abs(obj[1]-self.player0pos[1]) > 1)) or (self.map[obj[0], obj[1], 1] and self.player0)):
                    return ValueError("Invalid position")
            elif (((abs(obj[0]-self.player1pos[0]) > 1) or (abs(obj[1]-self.player1pos[1]) > 1)) or (self.map[obj[0], obj[1], 0] and not (self.player0))):
                return ValueError("Invalid position")
            if self.player0:
                self.map[self.player0pos[0], self.player0pos[1], 0] = False
                self.map[obj[0], obj[1], 0] = True
                if not (self.map[obj[0], obj[1], 4]):
                    self.map[obj[0], obj[1], 2] = True
                self.player0pos = [obj[0], obj[1]]
            else:
                self.map[self.player1pos[0], self.player1pos[1], 1] = False
                self.map[obj[0], obj[1], 1] = True
                if not (self.map[obj[0], obj[1], 4]):
                    self.map[obj[0], obj[1], 3] = True
                self.player1pos = [obj[0], obj[1]]
            #self.__find(obj, player)
            print('find', obj)
        else:
            t = tuple(np.argwhere(self.map[:, :, 0] == True))
            if t is not None:
                if (abs(t[0][0]-self.player0pos[0]) > 1 or abs(t[0][1]-self.player0pos[1]) > 1) or self.map[t[0][0], t[0][1], 0] or self.map[t[0][0], t[0][1], 1]:
                    return ValueError("Invalid position")
                else:
                    self.map[self.player0pos[0], self.player0pos[1], 0] = False
                    self.map[t[0][0], t[0][1], 0] = True
                    if not (self.map[t[0][0], t[0][1], 4]):
                        self.map[t[0][0], t[0][1], 2] = True
                    self.player0pos = [t[0][0], t[0][1]]
                    #self.__find([t[0][0], t[0][1]], 0)
            else:
                t = tuple(np.argwhere(self.map[:, :, 1] == True))
                if (abs(t[0][0]-self.player1pos[0]) > 1 or abs(t[0][1]-self.player1pos[1]) > 1) or self.map[t[0][0], t[0][1], 0] or self.map[t[0][0], t[0][1], 1]:
                    return ValueError("Invalid position")
                else:
                    self.map[self.player1pos[0], self.player1pos[1], 1] = False
                    self.map[t[0][0], t[0][1], 1] = True
                    if not (self.map[t[0][0], t[0][1], 4]):
                        self.map[t[0][0], t[0][1], 3] = True
                    self.player1pos = [t[0][0], t[0][1]]
                    #self.__find([t[0][0], t[0][1]], 0)

        if len(np.unique(np.logical_or(self.map[:, :, 2], self.map[:, :, 3]))) < 2:
            if np.count_nonzero(self.map[:, :, 2]) > np.count_nonzero(self.map[:, :, 3]):
                return 201
            else:
                return 202
        else:
            print(self.map[self.player0pos[0], self.player0pos[1], 0])
            # print(self.map[self.player1pos])
            return self.map
