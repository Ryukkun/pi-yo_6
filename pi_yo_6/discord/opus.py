import ctypes
import struct


from discord.opus import Decoder as DiscordDecoder
from discord.opus import _lib, is_loaded, _load_default, OpusError, c_float_ptr


# def libopus_loader(name: str) -> Any:
#     # create the library...
#     lib = ctypes.cdll.LoadLibrary(name)

#     # register the functions...
#     for item in exported_functions:
#         func = getattr(lib, item[0])

#         try:
#             if item[1]:
#                 func.argtypes = item[1]

#             func.restype = item[2]
#         except KeyError:
#             pass

#         try:
#             if item[3]:
#                 func.errcheck = item[3]
#         except KeyError:
#             pass

#     return lib


# def _load_default() -> bool:
#     global _lib
#     try:
#         if sys.platform == 'win32':
#             _basedir = os.path.dirname(os.path.abspath(__file__))
#             _bitness = struct.calcsize('P') * 8
#             _target = 'x64' if _bitness > 32 else 'x86'
#             _filename = os.path.join(_basedir, 'bin', f'libopus-0.{_target}.dll')
#             _lib = libopus_loader(_filename)
#         else:
#             # This is handled in the exception case
#             _lib = libopus_loader(ctypes.util.find_library('opus'))  # type: ignore
#     except Exception:
#         _lib = None

#     return _lib is not None


# def load_opus(name: str) -> None:
#     """Loads the libopus shared library for use with voice.
#     If this function is not called then the library uses the function
#     :func:`ctypes.util.find_library` and then loads that one if available.
#     Not loading a library and attempting to use PCM based AudioSources will
#     lead to voice not working.
#     This function propagates the exceptions thrown.
#     .. warning::
#         The bitness of the library must match the bitness of your python
#         interpreter. If the library is 64-bit then your python interpreter
#         must be 64-bit as well. Usually if there's a mismatch in bitness then
#         the load will throw an exception.
#     .. note::
#         On Windows, this function should not need to be called as the binaries
#         are automatically loaded.
#     .. note::
#         On Windows, the .dll extension is not necessary. However, on Linux
#         the full extension is required to load the library, e.g. ``libopus.so.1``.
#         On Linux however, :func:`ctypes.util.find_library` will usually find the library automatically
#         without you having to call this.
#     Parameters
#     ----------
#     name: :class:`str`
#         The filename of the shared library.
#     """
#     global _lib
#     _lib = libopus_loader(name)


# def is_loaded() -> bool:
#     """Function to check if opus lib is successfully loaded either
#     via the :func:`ctypes.util.find_library` call of :func:`load_opus`.
#     This must return ``True`` for voice to work.
#     Returns
#     -------
#     :class:`bool`
#         Indicates if the opus library has been loaded.
#     """
#     global _lib
#     return _lib is not None

class Decoder(DiscordDecoder):
    SAMPLING_RATE = 16000
    CHANNELS = 1
    SAMPLE_SIZE = struct.calcsize('h') * CHANNELS
        
    def packet_get_nb_channels(self, data: bytes) -> int:
        return 1
    
    def decode_float(self, data, *, fec=False):
        if not is_loaded():
            _load_default()
        if data is None and fec:
            raise OpusError("Invalid arguments: FEC cannot be used with null data")

        if data is None:
            frame_size = self._get_last_packet_duration() or self.SAMPLES_PER_FRAME
            channel_count = self.CHANNELS
        else:
            frames = self.packet_get_nb_frames(data)
            channel_count = self.packet_get_nb_channels(data)
            samples_per_frame = self.packet_get_samples_per_frame(data)
            frame_size = frames * samples_per_frame

        pcm = (ctypes.c_float * (frame_size * channel_count))()
        pcm_ptr = ctypes.cast(pcm, c_float_ptr)

        ret = _lib.opus_decode_float(self._state, data, len(data) if data else 0, pcm_ptr, frame_size, fec)

        return pcm[:ret * channel_count]
    

class Opus_Packet:
    SAMPLING_RATE = 48000
    CHANNELS = 2
    