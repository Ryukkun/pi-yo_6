import threading
import asyncio
import time

import numpy as np

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
        self.MLoop = False
        self.VLoop = False
        self.CLoop = client.loop
        self.Parent = parent
        self.Music = _APlayer(self,'M')
        self.Voice = _APlayer(self,'V')
        self.MBytes = None
        self.VBytes = None
        self.vc.encoder = opus.Encoder()
        self.play_audio = self.vc.send_audio_packet
        self.old_time = 0


    def speaking(self,CH,status):
        """
        これ（self._speak）がないと謎にバグる ※botがjoinしたときに居たメンツにしか 音が聞こえない
        友達が幻聴を聞いてたら怖いよね
        ついでにLOOPの制御も
        """
        if status:
            if self.VLoop == False and self.MLoop == False:
                self._speak(SpeakingState.voice)
        else:
            if self.VLoop and self.MLoop: pass
            elif self.VLoop or self.MLoop:
                self._speak(SpeakingState.none)
        if CH == 'V':
            self.VLoop = status
        if CH == 'M':
            self.MLoop = status

    def _speak(self, speaking: SpeakingState) -> None:
            try:
                asyncio.run_coroutine_threadsafe(self.vc.ws.speak(speaking), self.vc.client.loop)
            except Exception:
                pass



    def run(self):
        """
        これずっとloopしてます 止まりません loopの悪魔
        音声データ（Bytes）を取得し、必要があれば Numpy で読み込んで 合成しています
        最後に音声データ送信　ドルチェ
        """
        while self.loop:
            self.MBytes = self.Music.read_bytes()
            self.VBytes = self.Voice.read_bytes()
            VArray = None
            MArray = None

            if self.MBytes == 'Fin':
                self.Music.After()
                self.MBytes = None
            elif self.MBytes:
                # 秒数更新のため
                if ((self.Music.Timer - 1) % 500) == 0:
                    self.CLoop.create_task(self.Parent.Music.Update_Embed())
                
                MArray = np.frombuffer(self.MBytes,np.int16)
                self.Bytes = self.MBytes
            if self.VBytes == 'Fin':
                self.Voice.After()
                self.VBytes = None
            elif self.VBytes:
                VArray = np.frombuffer(self.VBytes,np.int16)
                self.Bytes = self.VBytes

            # Bytes Mix
            if type(MArray) != NoneType and type(VArray) != NoneType:
                self.Bytes = (MArray + VArray).astype(np.int16).tobytes()

            # Loop Delay
            PTime = time.time() - self.old_time
            if 0 <= PTime <= 0.02:
                time.sleep(0.02 - PTime)
            else:
                print(PTime)
                pass
            self.old_time = time.time()
            #print(PTime)
            # Send Bytes
            if self.MBytes or self.VBytes:
                try:self.play_audio(self.Bytes,encode=True)
                except OSError:
                    print('Error send_audio_packet OSError')
                    time.sleep(1)

            

class _APlayer():
    def __init__(self,parent,name):
        self.AudioSource = None
        self._SAD = None
        self.Pausing = False
        self.Parent = parent
        self.Timer = 0
        self.After = None
        self.Name = name
        self.QBytes = None
        self.Duration = None

        

    async def play(self,_SAD,after):
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
        self.Parent.speaking(self.Name,False)

    def resume(self):
        self.Pausing = False
        self.Parent.speaking(self.Name,True)

    def pause(self):
        self.Pausing = True
        self.Parent.speaking(self.Name,False)

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
                return temp
            if Bytes := self.AudioSource.read():
                self.Timer += 1
                return Bytes
            else:
                self.AudioSource = None
                self._SAD = None
                self.Parent.speaking(self.Name,False)
                return 'Fin'
            
        return None