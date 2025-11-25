from __future__ import annotations

import logging
from dataclasses import dataclass
from pathlib import Path

from src.core.config import AppConfig
from src.domain.models import TranscriptionResult, TranscriptionSegment

logger = logging.getLogger(__name__)


@dataclass
class OpenAIWhisperProvider:
	"""Cloud transcription using OpenAI API (Whisper / gpt‑4o‑mini‑transcribe)."""

	config: AppConfig

	def _client(self):
		try:
			from openai import OpenAI  # type: ignore
		except Exception as exc:  # pragma: no cover
			raise RuntimeError("Модуль 'openai' не установлен: pip install openai") from exc
		if not self.config.openai_api_key:
			raise RuntimeError("OPENAI_API_KEY не задан в .env")
		return OpenAI(api_key=self.config.openai_api_key)

	def _try_transcribe(self, model: str, wav_path: Path) -> TranscriptionResult:
		client = self._client()
		with wav_path.open("rb") as f:
			# verbose_json expected to include segments + language if available
			res = client.audio.transcriptions.create(  # type: ignore[attr-defined]
				model=model,
				file=f,
				response_format="verbose_json",
			)

		segments: list[TranscriptionSegment] = []
		language: str | None = None
		text: str = getattr(res, "text", "") or ""

		if hasattr(res, "segments") and res.segments:
			for seg in res.segments:
				start = float(getattr(seg, "start", 0.0) or 0.0)
				end = float(getattr(seg, "end", 0.0) or 0.0)
				seg_text = getattr(seg, "text", "")
				segments.append(TranscriptionSegment(start=start, end=end, text=seg_text))
		if hasattr(res, "language"):
			language = res.language

		return TranscriptionResult(
			text=text, language=language, segments=segments, provider=f"cloud:{model}"
		)

	def transcribe(self, wav_path: Path) -> TranscriptionResult:
		"""Transcribe with configured OpenAI model, fallback to whisper-1 if needed."""
		model = self.config.cloud.model or "gpt-4o-mini-transcribe"
		logger.info(f"Transcribing with OpenAI model: {model}")
		try:
			return self._try_transcribe(model, wav_path)
		except Exception as e:
			logger.warning(f"Model {model} failed: {e}, falling back to whisper-1")
			# fallback to whisper-1 for compatibility
			return self._try_transcribe("whisper-1", wav_path)



