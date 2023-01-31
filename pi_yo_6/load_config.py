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



def dif_config(file, cf_file):
    with open(file, 'r', encoding='utf-8') as f, \
         open(cf_file, 'r', encoding='utf-8') as cf:
            
        line_num = 0
        comment = False
        f_lines = f.readlines()
        cf_lines = cf.readlines()

    for cf_text in cf_lines:
        if line_num < len(f_lines):
            f_text:str = f_lines[line_num]
            f_text_pre = f_text.split('=')[0]
        else:
            f_text = ''

        if cf_text == f_text and "'''" in cf_text:
            comment = not comment

        if comment:
            line_num += 1
            continue

        if not f_text_pre in cf_text:
            f_lines.insert(line_num, cf_text)
        line_num += 1

    with open(file, 'w', encoding='utf-8') as f:
        f.write( ''.join(f_lines) )
    #print(''.join(f_lines))