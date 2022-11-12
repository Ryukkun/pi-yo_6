import json
from config import Guild_Config
from os import path

def Check(gid):
    GC_Path = f'{Guild_Config}{gid}.json'
    if not path.isfile(GC_Path):
        GC = {
            'auto_join':False,
            'admin_only':True,
            'volume':{'master':100, 'music':100, 'voice':100}
        }
        with open(GC_Path,'w') as f:
            json.dump(GC, f, indent=2)


def Read(gid):
    Check(gid)
    GC_Path = f'{Guild_Config}{gid}.json'
    with open(GC_Path,'r') as f:
       return json.load(f)


def Write(gid, GC):
    GC_Path = f'{Guild_Config}{gid}.json'
    with open(GC_Path,'w') as f:
        json.dump(GC, f, indent=2)