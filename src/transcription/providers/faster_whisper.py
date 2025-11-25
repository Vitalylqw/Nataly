from __future__ import annotations

import logging
import os
from dataclasses import dataclass
from pathlib import Path

from src.core.config import AppConfig
from src.domain.models import TranscriptionResult, TranscriptionSegment

logger = logging.getLogger(__name__)

try:
	from faster_whisper import WhisperModel  # type: ignore
except Exception:  # pragma: no cover - optional at import time
	WhisperModel = None  # type: ignore


@dataclass
class FasterWhisperProvider:
	"""Local GPU/CPU transcription via faster-whisper (CTranslate2)."""

	config: AppConfig
	_model: object | None = None

	def _ensure_model(self) -> None:
		if self._model is not None:
			return
		if WhisperModel is None:  # pragma: no cover - informative error
			raise RuntimeError(
				"Модуль 'faster-whisper' не найден. "
				"Установите зависимость: pip install faster-whisper"
			)
		
		# Construct path to local model: var/models/faster-whisper-{model_name}
		model_dir = Path(self.config.paths.model_dir).resolve()
		model_name = self.config.local.model
		# Check for prefixed directory first (e.g. faster-whisper-large-v3)
		local_model_path = model_dir / f"faster-whisper-{model_name}"
		
		if not local_model_path.exists():
			# Fallback to non-prefixed just in case
			local_model_path = model_dir / model_name

		logger.info(
			f"Loading faster-whisper model from local path: {local_model_path} "
			f"(device: {self.config.local.device}, compute: {self.config.local.compute_type})"
		)

		self._model = WhisperModel(
			str(local_model_path),
			device=self.config.local.device,
			compute_type=self.config.local.compute_type,
			local_files_only=True,
		)
		logger.info("Model loaded successfully")

	def transcribe(self, wav_path: Path) -> TranscriptionResult:
		"""Transcribe a wav file (16k mono) with faster-whisper.

		Returns:
			TranscriptionResult: aggregated text, language and segments.
		"""
		self._ensure_model()
		assert self._model is not None

		segments_iter, info = self._model.transcribe(  # type: ignore[attr-defined]
			str(wav_path),
			beam_size=self.config.local.beam_size,
			language=None,  # auto-detect
		)
		segments: list[TranscriptionSegment] = []
		text_parts: list[str] = []
		for seg in segments_iter:
			segments.append(
				TranscriptionSegment(start=seg.start or 0.0, end=seg.end or 0.0, text=seg.text)
			)
			if seg.text:
				text_parts.append(seg.text.strip())
		text = " ".join(t for t in text_parts if t)

		return TranscriptionResult(
			text=text,
			language=getattr(info, "language", None),
			segments=segments,
			provider="local:faster-whisper",
		)



