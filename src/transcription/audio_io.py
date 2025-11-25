from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

from src.core.config import AppConfig


def _resolve_bin(executable: str, ffmpeg_bin: str | None) -> str:
	"""Resolve ffmpeg/ffprobe binary path considering configured ffmpeg_bin."""
	if ffmpeg_bin:
		ff = Path(ffmpeg_bin)
		if executable == "ffmpeg":
			return str(ff)
		if executable == "ffprobe":
			return str(ff.with_name("ffprobe.exe" if ff.suffix.lower() == ".exe" else "ffprobe"))
	# fallback to PATH
	found = shutil.which(executable)
	if not found:
		raise RuntimeError(
			f"Не найден {executable}. Установите ffmpeg или запустите "
			f"scripts\\servises\\download_ffmpeg.bat и укажите путь в "
			f"paths.ffmpeg_bin в src/config/settings.yaml"
		)
	return found


def convert_to_wav_16k_mono(input_path: Path, output_path: Path, *, ffmpeg_bin: str | None) -> Path:
	"""Convert any audio to PCM s16le WAV 16kHz mono using ffmpeg.

	Args:
		input_path: source audio file path.
		output_path: destination .wav path.
		ffmpeg_bin: explicit ffmpeg path or None to use PATH.
	"""
	output_path.parent.mkdir(parents=True, exist_ok=True)
	cmd = [
		_resolve_bin("ffmpeg", ffmpeg_bin),
		"-y",
		"-hide_banner",
		"-loglevel",
		"error",
		"-i",
		str(input_path),
		"-ac",
		"1",
		"-ar",
		"16000",
		"-acodec",
		"pcm_s16le",
		str(output_path),
	]
	subprocess.run(cmd, check=True)
	return output_path


def ensure_wav_16k_mono(src_path: Path, *, config: AppConfig, dst_dir: Path) -> Path:
	"""Ensure input audio is converted to WAV 16kHz mono in dst_dir; return converted path."""
	dst_dir.mkdir(parents=True, exist_ok=True)
	out_path = dst_dir / (src_path.stem + "_16k_mono.wav")
	return convert_to_wav_16k_mono(src_path, out_path, ffmpeg_bin=config.paths.ffmpeg_bin)


def probe_duration_seconds(path: Path, *, ffmpeg_bin: str | None) -> float:
	"""Get media duration in seconds using ffprobe."""
	cmd = [
		_resolve_bin("ffprobe", ffmpeg_bin),
		"-v",
		"error",
		"-show_entries",
		"format=duration",
		"-of",
		"default=noprint_wrappers=1:nokey=1",
		str(path),
	]
	res = subprocess.run(cmd, capture_output=True, check=True, text=True)
	try:
		return float(res.stdout.strip())
	except ValueError as exc:
		raise RuntimeError(f"Не удалось определить длительность файла {path}") from exc


def safe_stem(name: str) -> str:
	"""Return filesystem-safe stem for filename (without extension)."""
	invalid = '<>:"/\\|?*'
	stem = Path(name).stem
	for ch in invalid:
		stem = stem.replace(ch, "_")
	return stem.strip() or "audio"



