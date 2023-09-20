import asyncio
import traceback
import logging
import re
import shutil
from os import path
from discord.utils import _ColourFormatter
from dataclasses import dataclass
from typing import Optional, List, Dict


def set_logger():
    library, _, _ = __name__.partition('.')
    logger = logging.getLogger(library)
    handler = logging.StreamHandler()
    handler.setFormatter(_ColourFormatter())
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)



class NoMetas(Exception):
    pass



@dataclass
class _SpeakerUnit:
    type:Optional[str] = None
    id:Optional[str] = None


@dataclass
class MessageUnit:
    text:Optional[str] = None
    speaker = _SpeakerUnit()
    speed:Optional[str] = None
    a:Optional[str] = None
    tone:Optional[str] = None
    intnation:Optional[str] = None
    out_path:Optional[str] = None







class DetectRunWrapper:
    def __init__(self, func, _class=None, _exception=False) -> None:
        self.is_running = False
        self.is_coroutine = asyncio.iscoroutinefunction(func)
        self.func = func
        self._class = _class
        self._exception = _exception
    

    def self_run(self, *args, **kwargs) -> None:
        if self._class:
            args = (self._class,) + args

        if self.is_coroutine:
            return self.async_run(*args, **kwargs)
        else:
            return self.sync_run(*args, **kwargs)


    async def async_run(self, *args, **kwargs) -> None:
        if self.is_running:
            if self._exception:
                raise Exception('This function is already running.')
            return
        self.is_running = True
        try:
            await self.func(*args, **kwargs)
        except:
            traceback.print_exc()
        finally:
            self.is_running = False
    

    def sync_run(self, *args, **kwargs) -> None:
        if self.is_running:
            if self._exception:
                raise Exception('This function is already running.')
            return
        self.is_running = True
        try:
            self.func(*args, **kwargs)
        except:
            traceback.print_exc()
        finally:
            self.is_running = False



    def __call__(self, *args, **kwds):
        return self.self_run(*args, **kwds)


    def __get__(self, obj, objtype):
        if obj is None:
            return self

        copy = DetectRunWrapper(self.func, _class=obj, _exception=self._exception)

        setattr(obj, self.func.__name__, copy)
        return copy


def detect_run(exception = False):
    def wrapper(func) -> DetectRunWrapper:
        return DetectRunWrapper(func, _exception=exception)

    return wrapper




class RunCheckStorageWrapper:
    def __init__(self, func, check_fin, _class= None):
        self.is_running = False
        self.func = func
        self._class = _class
        self.check_fin = check_fin
        self.is_coroutine = asyncio.iscoroutinefunction(func)


    def __call__(self, *args, **kwds):
        if self._class:
            args = (self._class,) + args
        return self.async_run(*args, **kwds) if self.is_coroutine else self.sync_run(*args, **kwds)


    def sync_run(self, *a, **k):
        res = self.func(*a, **k)

        if self.check_fin:
            self.is_running = False
        return res
    
    def set_running(self, status:bool):
        self.is_running = status


    async def async_run(self, *a, **k):
        res = await self.func(*a, **k)

        if self.check_fin:
            self.is_running = False
        return res


    def __get__(self, obj, objtype):
        if obj is None:
            return self

        copy = RunCheckStorageWrapper(self.func, self.check_fin, _class=obj)

        #print(getattr(obj, self.func.__name__) == self)
        setattr(obj, self.func.__name__, copy)
        # print(copy)
        # print("gettu")
        # print(obj)
        # print(self._class)
        # print(copy._class)
        # print(getattr(obj,self.func.__name__))
        # print(self)
        # print("")
        

        return copy



def run_check_storage(check_fin= True):
    def wapper(func) -> RunCheckStorageWrapper:
        return RunCheckStorageWrapper(func, check_fin)
    
    return wapper




re_class = re.compile(r'class (.+):')
re_var = re.compile(r'\s*(.+?)\s*=\s*(.+?) *\n')


class _class:
    def __init__(self, name) -> None:
        self.name = name
        self.comment:List[str] = []
        self.vars:List[Optional[Dict]] = []


def analysis_config(path):
    classes:List[_class] = []
    now_comment = False

    with open(path, 'r', encoding='utf-8') as f:
        texts = f.readlines()

    for text in texts:
        if "'''" in text:
            now_comment = not now_comment
            classes[-1].comment.append(text.rstrip())
            continue

        elif now_comment:
            classes[-1].comment.append(text.rstrip())
            continue


        if res := re_class.match(text):
            classes.append(_class(res.group(1)))
            
        elif res := re_var.match(text):
            classes[-1].vars.append({res.group(1) : res.group(2)})

        else:
            if classes:
                classes[-1].vars.append(None)    

    return classes



def check_config():
    template_path = './pi_yo_6/template/_config.py'
    target_path = './config.py'

    if not path.isfile(target_path):
        shutil.copyfile(template_path, target_path)
        return


    template_classes = analysis_config(template_path)
    target_classes = analysis_config(target_path)
    
    for target_class in target_classes:

        # find template class
        template_class = None
        for _ in template_classes:
            if target_class.name == _.name:
                template_class = _
                break
        if not template_class:
            continue
        
        # check var
        for target_var in target_class.vars:
            if not target_var: continue

            # find template var
            key, value = list(target_var.items())[0]
            for _ in template_class.vars:
                if not _: continue

                if _.get(key):
                    _[key] = value
                    break


    # result to str
    text_list = []
    for _c in template_classes:
        text_list.append(f'class {_c.name}:')
        text_list += _c.comment

        for _v in _c.vars:
            if _v:
                key, value = list(_v.items())[0]
                text_list.append(f'    {key} = {value}')
            
            else:
                text_list.append('')

    
    with open(target_path, 'w',encoding='utf-8') as f:
        f.write('\n'.join(text_list))