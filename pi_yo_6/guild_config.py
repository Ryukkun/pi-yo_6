import json
from config import Config
from os import path

class GC:
    @classmethod
    def Check(self, gid):
        GC_Path = f'{Config.Guild_Config}{gid}.json'
        if not path.isfile(GC_Path):
            GC = {
                'auto_join':False
            }
            with open(GC_Path,'w') as f:
                json.dump(GC, f, indent=2)

    @classmethod
    def Read(self, gid):
        self.Check(gid)
        GC_Path = f'{Config.Guild_Config}{gid}.json'
        with open(GC_Path,'r') as f:
            return json.load(f)

    @classmethod
    def Write(self, gid, GC):
        GC_Path = f'{Config.Guild_Config}{gid}.json'
        with open(GC_Path,'w') as f:
            json.dump(GC, f, indent=2)