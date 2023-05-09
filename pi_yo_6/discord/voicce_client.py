import nacl.secret
import time
import asyncio
import wave
import io
import numpy as np

from itertools import zip_longest
from typing import List, Optional

from discord import VoiceClient
from discord.gateway import DiscordVoiceWebSocket
from collections import defaultdict

from concurrent.futures import ThreadPoolExecutor
import struct

from pi_yo_6.discord.opus import Decoder, Opus_Packet



class MyVoiceWebSocket(DiscordVoiceWebSocket):
    def __init__(self, socket, loop,*, hook=None):
        super().__init__(socket, loop, hook=hook)
        self.record_ready = False

    async def received_message(self, msg):
        await super().received_message(msg)
        op = msg['op']

        if op == self.SESSION_DESCRIPTION:  # op 5
            self.record_ready = True


class MyVoiceClient(VoiceClient):
    def __init__(self, client, channel):
        super().__init__(client, channel)
        self.buffer:Optional[BufferDecoder] = None
        self.is_recording = False

    async def connect_websocket(self) -> MyVoiceWebSocket:
        ws = await MyVoiceWebSocket.from_client(self)
        self._connected.clear()
        while ws.secret_key is None:
            await ws.poll_event()
        self._connected.set()
        return ws

    def decrypt_xsalsa20_poly1305(self, data: bytes) -> tuple:
        box = nacl.secret.SecretBox(bytes(self.secret_key))
        is_rtcp = 200 <= data[1] < 205
        if is_rtcp:
            header, encrypted = data[:8], data[8:]
            nonce = bytearray(24)
            nonce[:8] = header
        else:
            header, encrypted = data[:12], data[12:]
            nonce = bytearray(24)
            nonce[:12] = header
        return header, box.decrypt(bytes(encrypted), bytes(nonce))

    def decrypt_xsalsa20_poly1305_suffix(self, data: bytes) -> tuple:
        box = nacl.secret.SecretBox(bytes(self.secret_key))
        is_rtcp = 200 <= data[1] < 205
        if is_rtcp:
            header, encrypted, nonce = data[:8], data[8:-24], data[-24:]
        else:
            header, encrypted, nonce = data[:12], data[12:-24], data[-24:]
        return header, box.decrypt(bytes(encrypted), bytes(nonce))

    def decrypt_xsalsa20_poly1305_lite(self, data: bytes) -> tuple:
        box = nacl.secret.SecretBox(bytes(self.secret_key))
        is_rtcp = 200 <= data[1] < 205
        if is_rtcp:
            header, encrypted, _nonce = data[:8], data[8:-4], data[-4:]
        else:
            header, encrypted, _nonce = data[:12], data[12:-4], data[-4:]
        nonce = bytearray(24)
        nonce[:4] = _nonce
        return header, box.decrypt(bytes(encrypted), bytes(nonce))

    async def recv_voice_packet(self):
        if not self.ws.record_ready:
            raise ValueError("Not Record Ready")

        start_time = time.perf_counter()
        while self.is_recording:
            recv = await self.loop.sock_recv(self.socket, 2 ** 16)

            if time.perf_counter() < (start_time + 0.02):
                continue

            if 200 <= recv[1] < 205:
                continue
            
            decrypt_func = getattr(self, f'decrypt_{self.mode}')
            header, data = decrypt_func(recv)
            packet = RTCPacket(header, data)
            packet._calc_extension_header_length()
            await self.buffer.recv_packet(packet)

    def record_start(self):
        if self.is_recording:
            raise ValueError("Already recording")

        # init
        self.is_recording = True
        self.buffer = BufferDecoder(self)

        # do record
        self.client.loop.create_task( self.recv_voice_packet())


    def record_fin(self):
        self.is_recording = False
        self.buffer.finish()



class RTCPacket:
    decoder = Decoder()
    none_data = np.frombuffer(decoder.decode(None), dtype=np.int16)
    exe = ThreadPoolExecutor(1)

    def __init__(self, header, decrypted):
        self.version = (header[0] & 0b11000000) >> 6
        self.padding = (header[0] & 0b00100000) >> 5
        self.extend = (header[0] & 0b00010000) >> 4
        self.cc = header[0] & 0b00001111
        self.marker = header[1] >> 7
        self.payload_type = header[1] & 0b01111111
        self.offset = 0
        self.ext_length = None
        self.ext_header = None
        self.csrcs = None
        self.profile = None
        self.real_time = time.perf_counter()

        self.header = header
        self.decrypted = decrypted
        self.seq, self.timestamp, self.ssrc = struct.unpack_from('>HII', header, 2)
        


    def _calc_extension_header_length(self) -> None:
        if not (self.decrypted[0] == 0xbe and self.decrypted[1] == 0xde and len(self.decrypted) > 4):
            return
        self.ext_length = int.from_bytes(self.decrypted[2:4], "big")
        offset = 4
        for i in range(self.ext_length):
            byte_ = self.decrypted[offset]
            offset += 1
            if byte_ == 0:
                continue
            offset += 1 + (0b1111 & (byte_ >> 4))

        # Discordの仕様
        if self.decrypted[offset + 1] in [0, 2]:
            offset += 1
        self.decrypted = self.decrypted[offset + 1:]
        
        # decode : opus -> wav
        data = self.decoder.decode(self.decrypted)
        data = np.frombuffer(data,dtype=np.int16)
        self.pcm_decrypted = data

    async def decode(self, loop:asyncio.BaseEventLoop):
        await loop.run_in_executor(self.exe, self._calc_extension_header_length)


class BufferDecoder:
    MAX_SRC = 65535
    SEQ_1 = int(MAX_SRC / 3)
    SEQ_2 = int(MAX_SRC / 3 * 2)
    SILENT_TIME = 0.2
    FINISH_DETECT_LIMIT = 1.5
    
    
    def __init__(self, vc:MyVoiceClient):
        self.queues:dict[int, List[RTCPacket]] = defaultdict(list)
        self.speaking_queues:dict[int, List[List[RTCPacket]]] = defaultdict(list)
        self.last_packet:dict[int, RTCPacket] = {}
        self.split_point = 0
        self.finish_bool = False
        self.vc = vc
        self.loop = vc.client.loop


    async def recv_packet(self, packet:RTCPacket):
        ssrc = packet.ssrc
        if self.last_packet.get(ssrc):
            # {Packet} xxxx ..... xxxxx {Last}
            if 0 <= packet.seq <= self.SEQ_1 and self.SEQ_2 <= self.last_packet[ssrc].seq <= self.MAX_SRC:
                self.split_point += 1
            
            # {Last} xxxx ..... xxxxx {Packet}
            elif 0 <= self.last_packet[ssrc].seq <= self.SEQ_1 and self.SEQ_2 <= packet.seq <= self.MAX_SRC:
                self.split_point -= 1

        # last_packet == None  ,  {Packet} xxxx .....
        elif 0 <= packet.seq <= self.SEQ_1:
            self.split_point += 1

        # seq 調節
        self.last_packet[ssrc] = packet
        packet.seq = packet.seq + ((self.MAX_SRC + 1) * self.split_point)
        self.queues[ssrc].append(packet)

        # speaking_chunk
        self.loop.create_task(self._speaking_chunk(packet))
        self.loop.create_task(self._detect_finish(packet))
        
        

    async def _speaking_chunk(self, packet:RTCPacket):
        await asyncio.sleep(self.SILENT_TIME)
        queues = self.queues[packet.ssrc]
        speaking_queues = self.speaking_queues[packet.ssrc]

        if queues:
            if queues[-1].timestamp == packet.timestamp:
                if 5 < len(queues):
                    speaking_queues.append(queues.copy())
                    
                queues.clear()
    

    async def _detect_finish(self, packet:RTCPacket):
        await asyncio.sleep(self.FINISH_DETECT_LIMIT)
        ssrc = packet.ssrc

        if self.last_packet:
            _last_packet = list(self.last_packet.values())
            _last_packet.sort(key=lambda x:x.real_time)
            _last_packet = _last_packet[-1]
            if _last_packet.timestamp == packet.timestamp:
                self.vc.record_fin()


    def _decode(self, data:List[RTCPacket]) -> np.ndarray:
        pcm = []
        start_time = None

        last_timestamp = None

        for packet in data:
            if packet is None:
                # パケット破損の場合
                pcm.append(RTCPacket.none_data)
                last_timestamp = None
                continue

            if start_time is None:
                start_time = packet.real_time
            else:
                start_time = min(packet.real_time, start_time)

            if len(packet.decrypted) < 10:
                # パケットがdiscordから送られてくる無音のデータだった場合: https://discord.com/developers/docs/topics/voice-connections#voice-data-interpolation
                last_timestamp = packet.timestamp
                continue
            #print(packet.timestamp)
            if last_timestamp is not None:
                elapsed = (packet.timestamp - last_timestamp) / Opus_Packet.SAMPLING_RATE
                if 0.02 < elapsed:
                    # 無音期間
                    margin = np.zeros(int(1.5*(elapsed - 0.02) * Decoder.SAMPLING_RATE), dtype=np.int16)
                    pcm.append(margin)

            data = packet.pcm_decrypted
            pcm.append(data)
            last_timestamp = packet.timestamp

        pcm = np.concatenate(pcm, dtype=np.int16)
        return pcm



    def finish(self):
        for key, value in self.queues.items():
            if 5 < len(value):
                self.speaking_queues[key].append(value)
        
        self.finish_bool = True


    async def get_speaking_chunk(self, ssrc=None):
        while True:
            for key, value in self.speaking_queues.items():
                if value:
                    value = value.pop(0)
                    value.sort(key=lambda x:x.seq)
                    try:
                        value = self._decode(value).astype(np.float32) / 32768.0
                    except Exception:
                        continue
                    return key, value
                
            if self.finish_bool:
                return None, None
            await asyncio.sleep(0.02)
