import threading
import asyncio
import time

import numpy as np

from json import load as json_load
from discord import opus, SpeakingState
from types import NoneType


class MultiAudio(threading.Thread):
    """
    Discord に存在する AudioPlayer は 同時に1つまでの音源の再生にしか対応していないため
    独自で Playerを作成 
    self.run は制御方法知らんから、常にループしてる 0.02秒(20ms) 間隔で 
    """
    def __init__(self,guild,client,parent) -> None:
        self.loop = True
        super(MultiAudio, self).__init__(daemon=True)
        self.guild = guild
        self.gid = guild.id
        self.vc = guild.voice_client
        self.CLoop = client.loop
        self.Parent = parent
        self.Music = _APlayer(self)
        self.Voice = _APlayer(self)
        self.update_volume()
        self.vc.encoder = opus.Encoder()
        self.vc.encoder.set_expected_packet_loss_percent(0.0)
        self.play_audio = self.vc.send_audio_packet
        self.old_time = 0

    def update_volume(self):
        GC_Path = f'{self.Parent.config.Guild_Config}{self.gid}.json'
        with open(GC_Path,'r') as f:
            GC = json_load(f)
        self.Music.volume =  GC['volume']['music'] / 100
        self.Voice.volume =  GC['volume']['voice'] / 100
        self.master = GC['volume']['master'] / 100

    def speaking(self,status):
        """
        これ（self._speak）がないと謎にバグる ※botがjoinしたときに居たメンツにしか 音が聞こえない
        友達が幻聴を聞いてたら怖いよね
        ついでにLOOPの制御も
        """
        if status:
            if self.Voice.Loop == False and self.Music.Loop == False:
                self._speak(SpeakingState.voice)
        else:
            if self.Voice.Loop and self.Music.Loop: pass
            elif self.Voice.Loop or self.Music.Loop:
                self._speak(SpeakingState.none)

    def _speak(self, speaking: SpeakingState) -> None:
            try:
                asyncio.run_coroutine_threadsafe(self.vc.ws.speak(speaking), self.vc.client.loop)
            except Exception:
                pass

    def _update_embed(self):
        # 秒数更新のため
        if 0 <= self.Music.Timer < (50*60):
            if (self.Music.Timer % (50*5)) == 1:
                self.CLoop.create_task(self.Parent.Music.Update_Embed())
        elif (50*60) <= self.Music.Timer < (50*1800):
            if (self.Music.Timer % (50*10)) == 1:
                self.CLoop.create_task(self.Parent.Music.Update_Embed())
        elif (50*1800) <= self.Music.Timer:
            if (self.Music.Timer % (50*30)) == 1:
                self.CLoop.create_task(self.Parent.Music.Update_Embed())


    def run(self):
        """
        これずっとloopしてます 止まりません loopの悪魔
        音声データ（Bytes）を取得し、必要があれば Numpy で読み込んで 合成しています
        最後に音声データ送信　ドルチェ
        """
        _start = time.perf_counter()
        while self.loop:
            MBytes = self.Music.read_bytes()
            VBytes = self.Voice.read_bytes()
            Bytes = None

            # Bytes Mix
            if type(MBytes) != NoneType and type(VBytes) != NoneType:
                Bytes = MBytes + VBytes

            # 音楽音声
            elif type(MBytes) != NoneType:
                self._update_embed()
                Bytes = MBytes
            
            # 読み上げ音声
            elif type(VBytes) != NoneType:
                Bytes = VBytes

            # Loop Delay
            _start += 0.02
            delay = max(0, _start - time.perf_counter())
            time.sleep(delay)
 
            # Send Bytes
            if type(Bytes) != NoneType:
                Bytes = Bytes * self.master
                try:self.play_audio(Bytes.astype(np.int16).tobytes(), encode=True)
                except OSError:
                    print('Error send_audio_packet OSError')
                    time.sleep(1)

            

class _APlayer():
    def __init__(self,parent):
        self.AudioSource = None
        self._SAD = None
        self.Pausing = False
        self.Parent = parent
        self.Timer = 0
        self.After = None
        self.QBytes = None
        self.Duration = None
        self.Loop = False
        self.volume = 1
        

    def play(self,_SAD,after):
        self._SAD = _SAD
        self.Duration = _SAD.St_Sec
        AudioSource = _SAD.AudioSource()
        # 最初のロードは少し時間かかるから先にロード
        self.QBytes = AudioSource.read()
        self.AudioSource = AudioSource
        self.Timer = 0
        self.After = after
        self.resume()

    def stop(self):
        self.AudioSource = None
        self._SAD = None
        self.Loop = False
        self.Parent.speaking(False)

    def resume(self):
        self.Pausing = False
        self.Loop = True
        self.Parent.speaking(True)

    def pause(self):
        self.Pausing = True
        self.Loop = False
        self.Parent.speaking(False)

    def is_playing(self):
        if self._SAD:
            return True
        return False

    def is_paused(self):
        return self.Pausing
    
    def read_bytes(self):
        if self.AudioSource and self.Pausing == False:
            
            if self.QBytes:
                self.Timer += 1
                temp = self.QBytes
                self.QBytes = None
                return np.frombuffer(temp,np.int16) * self.volume
            if Bytes := self.AudioSource.read():
                self.Timer += 1
                return np.frombuffer(Bytes,np.int16) * self.volume
            else:
                self.AudioSource = None
                self._SAD = None
                self.Loop = False
                self.Parent.speaking(False)
                self.After()
            
        return None