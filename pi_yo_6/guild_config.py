import json
from os import path

class GC:
    def __init__(self, GConfig) -> None:
        self.GConfig = GConfig

    def Check(self, gid):
        GC_Path = f'{self.GConfig}{gid}.json'
        if not path.isfile(GC_Path):
            GC = {
                'auto_join':False
            }
            with open(GC_Path,'w') as f:
                json.dump(GC, f, indent=2)

    def Read(self, gid):
        self.Check(gid)
        GC_Path = f'{self.GConfig}{gid}.json'
        with open(GC_Path,'r') as f:
            return json.load(f)

    def Write(self, gid, GC):
        GC_Path = f'{self.GConfig}{gid}.json'
        with open(GC_Path,'w') as f:
            json.dump(GC, f, indent=2)