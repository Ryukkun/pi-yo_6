import asyncio
import traceback
import logging
import re
import shutil
from os import path
from discord.utils import _ColourFormatter
from dataclasses import dataclass
from typing import Optional, List, Dict, Callable, Any, Generic, TypeVar, Self, TypedDict
import threading
from concurrent.futures import ThreadPoolExecutor

T = TypeVar('T')


def set_logger():
    library, _, _ = __name__.partition('.')
    logger = logging.getLogger(library)
    handler = logging.StreamHandler()
    handler.setFormatter(_ColourFormatter())
    logger.setLevel(logging.INFO)
    logger.addHandler(handler)



class NoMetas(Exception):
    pass



class StyleMeta(TypedDict):
    name: str
    id: str

# 2. スピーカー全体の構造を定義
class SpeakerMeta(TypedDict):
    name: str
    styles: List[StyleMeta]




class WrapperAbstract:
    """
    一度しか実行できないように

    メソッドにデコレータを付与することで実装
    実装クラスがimportで読み込まれた時点で_class=Noneのインスタンスが生成される
    実装クラスがインスタンス化された後、呼び出される際に __get__ , __call__ の順で呼び出される
    """
    def __init__(self, func:Callable[..., Any], _class:object=None):
        self.func = func
        self._class = _class

    def _new_instance(self, obj):
        return WrapperAbstract(self.func, _class=obj)

    def __get__(self, obj:object, objtype) -> Self:
        """
        このインスタンスが参照された場合に呼び出される

        Parameters
        ----------
        obj : Any
            参照元のオブジェクト(実装元のクラス)  クラスメソッドとして呼び出されたらNoneとなる 
        objtype : type
            参照元のオブジェクトのクラス

        Returns
        -------
        RunCheckStorageWrapper
            ラップされた関数
        """
        if obj is None:
            # クラスメソッドとして呼び出されたため処理は不要
            return self
        
        if self._class is not None:
            # _Classがあるってことは すでにラップされてる
            return self
        
        # インスタンスメソッドとして呼び出されたため、新しいラッパーを上書きし返す
        wrapper = self._new_instance(obj)
        # objの self.func.__name__[str] に wrapper をセットする
        setattr(obj, self.func.__name__, wrapper)
        return wrapper  # type: ignore


class RunCheckStorageWrapper(WrapperAbstract, Generic[T]):
    """
    一度しか実行できないように

    メソッドにデコレータを付与することで実装
    実装クラスがimportで読み込まれた時点で_class=Noneのインスタンスが生成される
    実装クラスがインスタンス化された後、呼び出される際に __get__ , __call__ の順で呼び出される
    """
    def __init__(self, func:Callable[..., T], check_fin:bool, _class:object=None):
        self.func: Callable[..., T]
        super().__init__(func, _class)
        self.is_running = False
        self.check_fin = check_fin
        self.is_coroutine = asyncio.iscoroutinefunction(func)
        self.exe = None
        self.lock = threading.Lock()


    def __call__(self, *args:Any, **kwargs:Any) -> T:
        if self.is_running:
            raise Exception(f'{self.func.__name__} is already running')
        self.is_running = True
        if self._class:
            args = (self._class,) + args
        return self._run(*args, **kwargs)


    def run_in_thread(self, *args:Any, **kwargs:Any):
        with self.lock:
            if self.is_running:
                raise Exception(f'{self.func.__name__} is already running')
            self.is_running = True
        if self._class:
            args = (self._class,) + args
        if not self.exe:
            self.exe = ThreadPoolExecutor(max_workers=1)
        self.exe.submit(self._run, *args, **kwargs)


    def __del__(self):
        if self.exe:
            self.exe.shutdown(wait=True)


    def _run(self, *args:Any, **kwargs:Any):
        try:
            return self.func(*args, **kwargs)
        finally:
            if self.check_fin:
                self.is_running = False

    def _new_instance(self, obj) -> 'RunCheckStorageWrapper':
        return RunCheckStorageWrapper(self.func, self.check_fin, _class=obj)


def run_check_storage(check_fin= True):
    def wapper(func) -> RunCheckStorageWrapper:
        return RunCheckStorageWrapper(func, check_fin)
    return wapper



class TaskRunningWrapper(WrapperAbstract, Generic[T]):
    def __init__(self, func:Callable[..., T], _class:object=None):
        super().__init__(func, _class)
        self.task: asyncio.Task | None = None

    def create_task(self, *args:Any, **kwargs:Any):
        if not self.is_running():
            args = (self._class,) + args
            self.task = asyncio.get_event_loop().create_task(self.func(*args, **kwargs))

    async def wait(self) -> T | None:
        if self.is_running():
            return await self.task # type: ignore
        return 
    
    async def run(self, *args:Any, **kwargs:Any) -> T:
        if self.task and not self.task.done():
            return await self.task
        self.create_task(*args, **kwargs)
        return await self.wait() # type: ignore
    
    def is_running(self) -> bool:
        if self.task is None:
            return False
        return not self.task.done()
    
    def cancel(self):
        if self.task and not self.task.done():
            self.task.cancel()
            self.task = None

    def _new_instance(self, obj:object):
        return TaskRunningWrapper(self.func, _class=obj)
    

def task_running_wrapper():
    def wapper(func) -> TaskRunningWrapper:
        return TaskRunningWrapper(func)
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