import json
from os import path

from config import Config

class GC:
    def __init__(self, gid) -> None:
        self.GConfig = Config.guild_config
        self.gid = gid
        self.GC_Path = f'{self.GConfig}{self.gid}.json'
        if not path.isfile(self.GC_Path):
            GC = {
                'auto_join':False,
                'admin_only':{},
                'voice':{}
            }
        else:
            with open(self.GC_Path,'r') as f:
                GC = json.load(f)
        if not GC.get('voice'):
            GC['voice'] = {}
        if not GC.get('admin_only'):
            GC['admin_only'] = {}
        self.Write(GC)

    def Read(self) -> dict:
        with open(self.GC_Path,'r') as f:
            return json.load(f)


    def Write(self, GC):
        with open(self.GC_Path,'w') as f:
            json.dump(GC, f, indent=2)


class UC:
    @classmethod
    def Read(self, uid):
        _path = f'{Config.user_config}{uid}.json'
        if not path.isfile(_path):
            GC = {
                'voice':-1
            }
        else:
            with open(_path,'r') as f:
                GC = json.load(f)
        # if not GC.get('voice'):
        #     GC['voice'] = {}
        self.Write(uid, GC)
        return GC

    @classmethod
    def Write(self, uid, GC):
        _path = f'{Config.user_config}{uid}.json'
        with open(_path,'w') as f:
            json.dump(GC, f, indent=2)