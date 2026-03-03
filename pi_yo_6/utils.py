import asyncio
from dataclasses import dataclass
import enum
import logging
from discord.utils import _ColourFormatter
from typing import List, Callable, Any, Generic, TypeVar, Self, TypedDict
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


class ENGINE_TYPE(str, enum.Enum):
    OPEN_JTALK = 'open_jtalk'
    VOICEVOX = 'voicevox'
    COEIROINK = 'coeiroink'


@dataclass
class VoiceUnit:
    type:ENGINE_TYPE = ENGINE_TYPE.OPEN_JTALK
    name:str = ""
    style:str = ""
    speed:float = 1.2
    tone:float = 0.0
    """= pitch"""
    intnation:float = 0.0