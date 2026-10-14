import wave
import io
import struct
import numpy as np
from scipy import signal
from typing import Tuple

# Pre-computed lookup table for 8-bit mu-law to 16-bit linear PCM decoding (Python 3.14+ compliant)
def _build_mulaw_table():
    table = np.zeros(256, dtype=np.int16)
    for i in range(256):
        sample = ~i
        sign = (sample & 0x80)
        exponent = (sample >> 4) & 0x07
        mantissa = sample & 0x0F
        magnitude = ((mantissa << 3) + 0x84) << exponent
        magnitude -= 0x84
        table[i] = -magnitude if sign != 0 else magnitude
    return table

MULAW_DECODE_TABLE = _build_mulaw_table()

class AudioProcessor:
    @staticmethod
    def decode_mulaw_to_pcm(mulaw_bytes: bytes) -> bytes:
        """Decodes 8kHz mu-law telephony payload into 16-bit linear PCM."""
        arr = np.frombuffer(mulaw_bytes, dtype=np.uint8)
        decoded = MULAW_DECODE_TABLE[arr]
        return decoded.tobytes()

    @staticmethod
    def resample_pcm(pcm_bytes: bytes, orig_sr: int = 8000, target_sr: int = 16000) -> bytes:
        """Resamples 16-bit linear mono PCM audio between sample rates."""
        if orig_sr == target_sr:
            return pcm_bytes

        data = np.frombuffer(pcm_bytes, dtype=np.int16)
        if len(data) == 0:
            return b""

        # Calculate target number of samples
        num_target_samples = int(len(data) * target_sr / orig_sr)
        resampled_data = signal.resample(data, num_target_samples).astype(np.int16)
        return resampled_data.tobytes()

    @staticmethod
    def pcm_to_wav(pcm_bytes: bytes, sample_rate: int = 16000, num_channels: int = 1) -> bytes:
        """Packages raw 16-bit PCM bytes into standard RIFF WAV container."""
        buffer = io.BytesIO()
        with wave.open(buffer, 'wb') as wf:
            wf.setnchannels(num_channels)
            wf.setsampwidth(2)  # 16-bit = 2 bytes
            wf.setframerate(sample_rate)
            wf.writeframes(pcm_bytes)
        buffer.seek(0)
        return buffer.read()

    @staticmethod
    def get_wav_duration_seconds(wav_bytes: bytes) -> float:
        """Inspects WAV header to determine total audio duration."""
        try:
            with wave.open(io.BytesIO(wav_bytes), 'rb') as wf:
                frames = wf.getnframes()
                rate = wf.getframerate()
                if rate > 0:
                    return round(frames / float(rate), 2)
        except Exception:
            pass
        return 0.0
