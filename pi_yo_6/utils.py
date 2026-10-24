import asyncio
from concurrent.futures import ThreadPoolExecutor
import enum
import threading
from typing import Any, Callable, Generic, Self, TypedDict, TypeVar

from pydantic import BaseModel

T = TypeVar('T')


class NoMetas(Exception):
    pass


class StyleMeta(TypedDict):
    name: str
    id: str


# 2. スピーカー全体の構造を定義
class SpeakerMeta(TypedDict):
    name: str
    styles: list[StyleMeta]


class WrapperAbstract:
    """
    一度しか実行できないように

    メソッドにデコレータを付与することで実装
    実装クラスがimportで読み込まれた時点で_class=Noneのインスタンスが生成される
    実装クラスがインスタンス化された後、呼び出される際に __get__ , __call__ の順で呼び出される
    """

    def __init__(self, func: Callable[..., Any], _class: object = None):
        self.func = func
        self._class = _class

    def _new_instance(self, obj: object) -> Self:
        return WrapperAbstract(self.func, _class=obj)  # type: ignore[return-value]

    def __get__(self, obj: object, objtype: type | None = None) -> Self:
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
        return wrapper


class RunCheckStorageWrapper(WrapperAbstract, Generic[T]):
    """
    一度しか実行できないように

    メソッドにデコレータを付与することで実装
    実装クラスがimportで読み込まれた時点で_class=Noneのインスタンスが生成される
    実装クラスがインスタンス化された後、呼び出される際に __get__ , __call__ の順で呼び出される
    """

    def __init__(self, func: Callable[..., T], check_fin: bool, _class: object = None):
        self.func: Callable[..., T]
        super().__init__(func, _class)
        self.is_running = False
        self.check_fin = check_fin
        self.is_coroutine = asyncio.iscoroutinefunction(func)
        self.exe: ThreadPoolExecutor | None = None
        self.lock = threading.Lock()

    def __call__(self, *args: Any, **kwargs: Any) -> T:
        with self.lock:
            if self.is_running:
                raise RuntimeError(f'{self.func.__name__} is already running')
            self.is_running = True
        if self._class:
            args = (self._class,) + args
        return self._run(*args, **kwargs)

    def run_in_thread(self, *args: Any, **kwargs: Any) -> None:
        with self.lock:
            if self.is_running:
                raise RuntimeError(f'{self.func.__name__} is already running')
            self.is_running = True
        if self._class:
            args = (self._class,) + args
        if not self.exe:
            self.exe = ThreadPoolExecutor(max_workers=1)
        self.exe.submit(self._run, *args, **kwargs)

    def __del__(self) -> None:
        if self.exe:
            self.exe.shutdown(wait=False)

    def _run(self, *args: Any, **kwargs: Any) -> T:
        try:
            return self.func(*args, **kwargs)
        finally:
            if self.check_fin:
                with self.lock:
                    self.is_running = False

    def _new_instance(self, obj: object) -> 'RunCheckStorageWrapper[T]':
        return RunCheckStorageWrapper(self.func, self.check_fin, _class=obj)


def run_check_storage(check_fin: bool = True) -> Callable[[Callable[..., T]], RunCheckStorageWrapper[T]]:
    def wrapper(func: Callable[..., T]) -> RunCheckStorageWrapper[T]:
        return RunCheckStorageWrapper(func, check_fin)

    return wrapper


class ENGINE_TYPE(str, enum.Enum):
    OPEN_JTALK = 'open_jtalk'
    VOICEVOX = 'voicevox'
    COEIROINK = 'coeiroink'


class VoiceUnit(BaseModel):
    type: ENGINE_TYPE = ENGINE_TYPE.OPEN_JTALK
    name: str = ""
    style: str = ""
    speed: float = 1.2
    tone: float = 0.0
    """= pitch"""
    intonation: float = 0.0

    def __str__(self) -> str:
        return (
            f"**Engine**: `{self.type.value}`\n"
            f"**Voice**: `{self.name}` (`{self.style}`)\n"
            f"**Speed**: `{self.speed}` / **Tone**: `{self.tone}` / **Intonation**: `{self.intonation}`"
        )
