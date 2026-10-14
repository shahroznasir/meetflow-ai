import pytest
import numpy as np
from app.services.audio_processor import AudioProcessor

def test_mulaw_decoding():
    # Synthetic mu-law encoded silence (0xFF in mu-law corresponds to 0 magnitude)
    mulaw_sample = bytes([0xFF] * 160)
    pcm_out = AudioProcessor.decode_mulaw_to_pcm(mulaw_sample)
    
    # 160 bytes of 8-bit mu-law should decode into 160 * 2 = 320 bytes of 16-bit PCM
    assert len(pcm_out) == 320
    data = np.frombuffer(pcm_out, dtype=np.int16)
    assert len(data) == 160

def test_pcm_resampling():
    # Generate 1-second sine wave at 8000 Hz
    t = np.linspace(0, 1.0, 8000, endpoint=False)
    sine_wave = (np.sin(2 * np.pi * 440 * t) * 10000).astype(np.int16)
    pcm_8k = sine_wave.tobytes()

    # Resample to 16000 Hz
    pcm_16k = AudioProcessor.resample_pcm(pcm_8k, orig_sr=8000, target_sr=16000)
    samples_16k = np.frombuffer(pcm_16k, dtype=np.int16)

    # Output should have 16000 samples (+/- 1 sample)
    assert abs(len(samples_16k) - 16000) <= 2

def test_pcm_to_wav_and_duration():
    # 1 second of 16kHz mono audio (32000 bytes)
    dummy_pcm = bytes(32000)
    wav_bytes = AudioProcessor.pcm_to_wav(dummy_pcm, sample_rate=16000, num_channels=1)

    assert wav_bytes.startswith(b"RIFF")
    duration = AudioProcessor.get_wav_duration_seconds(wav_bytes)
    assert duration == 1.0
