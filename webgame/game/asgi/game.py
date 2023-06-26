import time
import uuid
import numpy as np
from numba import njit
import numpy as np
import redis
from django.conf import settings



class Game:
    def __init__(self, map=None, player0=None, player1=None, playOne=True,Move=None):
        if map is None:
            self.player0 = playOne
            self.map = np.zeros((16, 16, 5), dtype=np.bool_)
            self.map[6, 9, 0] = True
            self.map[6, 9, 2] = True
            self.map[9, 6, 1] = True
            self.map[9, 6, 3] = True
            self.player0pos = np.array([6, 9])
            self.player1pos = np.array([9, 6])
            self.Move = Move
            self.score = [1,1]
        else:
            if player0 is not None:
                self.player0 = playOne
                self.map = np.asarray(map, dtype=np.bool_)
                self.player0pos = np.array(player0)
                self.player1pos = np.array(player1)
                self.score = [np.count_nonzero(self.map[:, :, 2]),np.count_nonzero(self.map[:, :, 3])]
            else:
                self.player0 = playOne
                self.map = np.asarray(map, dtype=np.bool_)
                self.player0pos = np.where(self.map[:, :, 0])
                self.player1pos = np.where(self.map[:, :, 1])
                self.score = [np.count_nonzero(self.map[:, :, 2]),np.count_nonzero(self.map[:, :, 3])]
    @property
    def player0pos(self):
        return self._player0pos
    @player0pos.setter
    def player0pos(self,value):
        self._player0pos = np.asarray(value,dtype=int)
    @property
    def player1pos(self):
        return self._player1pos
    @player1pos.setter
    def player1pos(self,value):
        self._player1pos = np.asarray(value,dtype=int)

    """
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

    """
    def __draw(self, list, player):
        for i in list:
            print(i)
            i.append(4)
            if self.map[tuple(i)]:
                continue
            else:
                self.map[tuple(i)] = True
                i[2] = player
                self.map[tuple(i)] = True

    def __check(self, list, player):
        self.c = []
        if len(list) != 3 and len(list) != 4:
            return False
        if len(list) == 3:
            l = None
            if list[0][0] == list[1][0]:
                if list[0][1] == list[2][1]:
                    rc = list[0]
                    l = [list[2], list[1]]
                elif list[1][1] == list[2][1]:
                    rc = list[1]
                    l = [list[0], list[2]]
            if list[1][0] == list[2][0]:
                if list[1][1] == list[0][1]:
                    rc = list[1]
                    l = [list[2], list[0]]
                elif list[2][1] == list[0][1]:
                    rc = list[2]
                    l = [list[0], list[1]]
            if list[0][0] == list[2][0]:
                if list[0][1] == list[1][1]:
                    rc = list[0]
                    l = [list[2], list[1]]
                elif list[2][1] == list[1][1]:
                    rc = list[2]
                    l = [list[0], list[1]]

            
            if l is not None:
                dx = l[0][0] - l[1][0]
                dy = l[0][1] - l[1][1]

                sign_x = -1 if dx > 0 else 1 if dx < 0 else 0
                sign_y = -1 if dy > 0 else 1 if dy < 0 else 0

                if dx < 0:
                    dx = -dx
                if dy < 0:
                    dy = -dy

                if dx > dy:
                    pdx, pdy = sign_x, 0
                    es, el = dy, dx
                else:
                    pdx, pdy = 0, sign_y
                    es, el = dx, dy

                x, y = l[0][0], l[0][1]

                error, t = el/2, 0

                while t < el:
                    if not (self.map[x, rc[1], player]) or not (self.map[x, y, player]):
                        print((self.map[x, rc[1], player]),
                              (self.map[x, y, player]))
                        return False
                    if rc[1] > y:
                        for i in range(rc[1], y+1):
                            self.c.append([x, i])
                    else:
                        for i in range(y, rc[1]+1):
                            self.c.append([x, i])
                    if rc[0] > x:
                        for i in range(x, rc[0]+1):
                            self.c.append([i, y])
                    else:
                        for i in range(rc[0], x+1):
                            self.c.append([i, y])
                    error -= es
                    if error < 0:
                        error += el
                        x += sign_x
                        y += sign_y
                    else:
                        x += pdx
                        y += pdy
                    t += 1
                if not (self.map[x, rc[1], player]) or not (self.map[x, y, player]):
                    print((self.map[x, rc[1], player]),
                          (self.map[x, y, player]))
                    return False
                if rc[1] > y:
                    for i in range(rc[1], y+1):
                        self.c.append([x, i])
                else:
                    for i in range(y, rc[1]+1):
                        self.c.append([x, i])
                if rc[0] > x:
                    for i in range(x, rc[0]+1):
                        self.c.append([i, y])
                else:
                    for i in range(rc[0], x+1):
                        self.c.append([i, y])
                return True
        if len(list) == 4:
            x1 = list[0][0]
            x2 = list[0][0]
            y1 = list[0][1]
            y2 = list[0][1]
            for i in list:

                x1 = i[0] if i[0] < x1 else x1
                x2 = i[0] if i[0] > x2 else x2
                y1 = i[1] if i[1] < y1 else y1
                y2 = i[1] if i[1] > y2 else y2
            for i in range(x1, x2+1):
                for j in range(y1, y2+1):
                    if i == x1 or i == x2 or j == y1 or j == y2:
                        if not (self.map[i, j, player]):
                            return False
                    self.c.append([i, j])

            return True
        return False

    def draw(self, list):
        if self.player0:
            player = 2
        else:
            player = 3
        if np.unique(list,axis=0).shape[0]> 1:
            if self.__check(list, player):
                print(self.c)
                self.__draw(self.c, player)
                if len(np.unique(np.logical_or(self.map[:, :, 2], self.map[:, :, 3]))) < 2:
                    if np.count_nonzero(self.map[:, :, 2]) > np.count_nonzero(self.map[:, :, 3]):
                        return 201
                    elif np.count_nonzero(self.map[:, :, 2]) < np.count_nonzero(self.map[:, :, 3]):
                        return 202
                    else:
                        return 203
                self.score = [np.count_nonzero(self.map[:, :, 2]),np.count_nonzero(self.map[:, :, 3])]
                return 1
            else:
                return -1
        else:
            return -1

    def move(self, obj):
        r = -1
        if self.player0:
            player = 2
        else:
            player = 3
        if np.shape(obj) != np.shape(self.map):
            if self.player0:
                if (((abs(obj[0]-self.player0pos[0]) > 1) or (abs(obj[1]-self.player0pos[1]) > 1)) or (self.map[obj[0], obj[1], 1] and self.player0)):
                    return ValueError("Invalid position")
                self.map[self.player0pos[0], self.player0pos[1], 0] = False
                self.map[obj[0], obj[1], 0] = True
                if not (self.map[obj[0], obj[1], 4]):
                    self.map[obj[0], obj[1], 2] = True
                    self.map[obj[0], obj[1], 3] = False
                self.player0pos = [obj[0], obj[1]]
                r =  0
            else:
                if (((abs(obj[0]-self.player1pos[0]) > 1) or (abs(obj[1]-self.player1pos[1]) > 1)) or (self.map[obj[0], obj[1], 0] and not (self.player0))):
                    return ValueError("Invalid position")
                self.map[self.player1pos[0], self.player1pos[1], 1] = False
                self.map[obj[0], obj[1], 1] = True
                if not (self.map[obj[0], obj[1], 4]):
                    self.map[obj[0], obj[1], 3] = True
                    self.map[obj[0], obj[1], 2] = False
                self.player1pos = [obj[0], obj[1]]
                r =  0

            # self.__find(obj, player)
            print('find', obj)
        else:
            t = tuple(np.argwhere(self.map[:, :, 0] == True))
            if t is not None:
                if (abs(t[0][0]-self.player0pos[0]) > 1 or abs(t[0][1]-self.player0pos[1]) > 1) or self.map[t[0][0], t[0][1], 0] or self.map[t[0][0], t[0][1], 1]:
                    return ValueError("Invalid position")
                else:
                    self.map[self.player0pos[0], self.player0pos[1], 0] = False
                    self.map[self.player0pos[0], self.player0pos[1], 2] = False
                    self.map[t[0][0], t[0][1], 0] = True
                    if not (self.map[t[0][0], t[0][1], 4]):
                        self.map[t[0][0], t[0][1], 2] = True
                    self.player0pos = [t[0][0], t[0][1]]
                    r =  0
                    # self.__find([t[0][0], t[0][1]], 0)
            else:
                t = tuple(np.argwhere(self.map[:, :, 1] == True))
                if (abs(t[0][0]-self.player1pos[0]) > 1 or abs(t[0][1]-self.player1pos[1]) > 1) or self.map[t[0][0], t[0][1], 0] or self.map[t[0][0], t[0][1], 1]:
                    return ValueError("Invalid position")
                else:
                    self.map[self.player1pos[0], self.player1pos[1], 1] = False
                    self.map[self.player0pos[0], self.player0pos[1], 3] = False
                    self.map[t[0][0], t[0][1], 1] = True
                    if not (self.map[t[0][0], t[0][1], 4]):
                        self.map[obj[0], obj[1], 3] = True
                    self.player1pos = [t[0][0], t[0][1]]
                    r = 0
                    # self.__find([t[0][0], t[0][1]], 0)
        if len(np.unique(np.logical_or(self.map[:, :, 2], self.map[:, :, 3]))) < 2:
            if np.count_nonzero(self.map[:, :, 2]) > np.count_nonzero(self.map[:, :, 3]):
                r =  201
            elif np.count_nonzero(self.map[:, :, 2]) < np.count_nonzero(self.map[:, :, 3]):
                r =  202
            else:
                r = 203
        self.score = [np.count_nonzero(self.map[:, :, 2]),np.count_nonzero(self.map[:, :, 3])]
        return r

class Memory:
    def __init__(self, redis_storage=None):
        self.redis_storage = redis.StrictRedis(
            host=settings.REDIS_HOST, port=settings.REDIS_PORT, db=1) if redis_storage is None else redis_storage

    def CreateGame(self, user0, user1, room: str):
        print(self.redis_storage.exists(room))
        self.user0 = user0
        self.user1 = user1
        if self.redis_storage.exists(room) == 1:
            print("exist game(M):", room)
            temp = self.redis_storage.lrange(room, 0, 5)
            map = np.frombuffer(temp[2], dtype=np.bool_).reshape((16, 16, 5))
            return map
        else:
            g = Game()
            print("created game(M):", room)
            self.redis_storage.rpush(
                room, *[user0, user1, g.map.tobytes(), g.player0pos.tobytes(), g.player1pos.tobytes(),user0])
            self.redis_storage.expire(room, 14400)

    def GetGame(self, room):
        print(room)
        if self.redis_storage.exists(room) == 1:
            temp = self.redis_storage.lrange(room, 0, 5)
            self.user0 = temp[0].decode()
            self.user1 = temp[1].decode()
            map = np.frombuffer(temp[2], dtype=np.bool_).reshape(
                (16, 16, 5)).tolist()
            p0 = np.frombuffer(temp[3], dtype=int).tolist()
            p1 = np.frombuffer(temp[4], dtype=int).tolist()
            self.move=temp[5].decode()
            return [self.user0, self.user1, map, p0, p1,self.move]
        else:
            return None

    def SaveGame(self, room, game, u0=None, u1=None,move=None):
        if (u0 is not None) and (u1 is not None):
            self.user0 = u0
            self.user1 = u1
        if isinstance(game,list):
            self.redis_storage.delete(room)
            self.redis_storage.rpush(room, *game)
            self.redis_storage.rpush(room, move)
            self.redis_storage.expire(room, 14400)
        elif isinstance(game,Game):
            self.redis_storage.delete(room)
            self.redis_storage.rpush(room, *[self.user0, self.user1, game.map.tobytes(
            ), game.player0pos.tobytes(), game.player1pos.tobytes(),move])
            self.redis_storage.expire(room, 14400)
        # if

    
    
    
    #def MoveGame(self, obj, room, user):
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
                room, *[temp[0], temp[1], game.map.tobytes(), game.player0pos.tobytes(), game.player1pos.tobytes(),])
            return game.map
        else:
            return None

    #def MoveGameMap(self, room, user, obj):
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
