from __future__ import annotations

import math
import subprocess
from pathlib import Path

from src.transcription.audio_io import _resolve_bin, probe_duration_seconds


def segment_wav_by_time(
	input_wav: Path,
	*,
	max_sec: int,
	output_dir: Path,
	ffmpeg_bin: str | None,
) -> list[Path]:
	"""Split WAV file into segments with maximum duration max_sec using ffmpeg segment muxer.

	Returns paths to created segments in order. If input shorter than max_sec, returns [input].
	"""
	output_dir.mkdir(parents=True, exist_ok=True)
	duration = probe_duration_seconds(input_wav, ffmpeg_bin=ffmpeg_bin)
	if duration <= max_sec + 0.5:
		return [input_wav]

	segments: list[Path] = []
	out_template = output_dir / (input_wav.stem + "_part_%03d.wav")
	cmd = [
		_resolve_bin("ffmpeg", ffmpeg_bin),
		"-y",
		"-hide_banner",
		"-loglevel",
		"error",
		"-i",
		str(input_wav),
		"-f",
		"segment",
		"-segment_time",
		str(max_sec),
		"-c",
		"copy",
		str(out_template),
	]
	subprocess.run(cmd, check=True)

	# Collect produced files
	count = math.ceil(duration / max_sec)
	for idx in range(count):
		p = output_dir / (input_wav.stem + f"_part_{idx:03d}.wav")
		if p.exists():
			segments.append(p)

	return segments



