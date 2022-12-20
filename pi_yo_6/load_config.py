import json
from os import path

class GC:
    def __init__(self, GConfig, gid) -> None:
        self.GConfig = GConfig
        self.gid = gid
        self.GC_Path = f'{self.GConfig}{self.gid}.json'

    def Read(self):
        if not path.isfile(self.GC_Path):
            GC = {
                'auto_join':False,
                'voice':{}
            }
        else:
            with open(self.GC_Path,'r') as f:
                GC = json.load(f)
        if not GC.get('voice'):
            GC['voice'] = {}
        self.Write(GC)
        return GC


    def Write(self, GC):
        with open(self.GC_Path,'w') as f:
            json.dump(GC, f, indent=2)


class UC:
    def __init__(self, uconfig) -> None:
        self.uconfig = uconfig

    def Read(self, uid):
        _path = f'{self.uconfig}{uid}.json'
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

    def Write(self, uid, GC):
        _path = f'{self.uconfig}{uid}.json'
        with open(_path,'w') as f:
            json.dump(GC, f, indent=2)