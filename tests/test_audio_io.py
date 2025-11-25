import math
import shutil
import struct
import wave
from pathlib import Path

import pytest

from src.core.config import load_config
from src.transcription.audio_io import convert_to_wav_16k_mono, probe_duration_seconds


def _generate_beep(path: Path, *, freq: float = 440.0, sec: float = 0.5, sr: int = 44100) -> None:
	n_samples = int(sr * sec)
	with wave.open(str(path), "w") as w:
		w.setnchannels(1)
		w.setsampwidth(2)  # 16-bit
		w.setframerate(sr)
		for i in range(n_samples):
			val = int(32767 * 0.3 * math.sin(2 * math.pi * freq * i / sr))
			w.writeframes(struct.pack("<h", val))


@pytest.mark.skipif(shutil.which("ffmpeg") is None, reason="ffmpeg not installed")
def test_convert_to_wav_16k_mono(tmp_path: Path) -> None:
	src = tmp_path / "src.wav"
	_generate_beep(src)
	cfg = load_config()
	dst = tmp_path / "out.wav"
	out = convert_to_wav_16k_mono(src, dst, ffmpeg_bin=cfg.paths.ffmpeg_bin)
	assert out.exists()
	# duration close to 0.5s
	dur = probe_duration_seconds(out, ffmpeg_bin=cfg.paths.ffmpeg_bin)
	assert 0.4 <= dur <= 0.6


