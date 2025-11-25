from __future__ import annotations

import concurrent.futures
import logging
from dataclasses import dataclass
from pathlib import Path
from typing import Protocol

from src.core.config import AppConfig
from src.core.storage import Storage
from src.domain.models import TranscriptionResult, TranscriptionSegment
from src.transcription.audio_io import ensure_wav_16k_mono
from src.transcription.chunking import segment_wav_by_time
from src.transcription.providers.faster_whisper import FasterWhisperProvider
from src.transcription.providers.openai_whisper import OpenAIWhisperProvider
from src.utils.hashing import sha256_of_file

logger = logging.getLogger(__name__)


class TranscriptionProvider(Protocol):
	def transcribe(self, wav_path: Path) -> TranscriptionResult:  # pragma: no cover - interface
		...


@dataclass
class TranscriptionRouter:
	config: AppConfig

	# Providers (lazy)
	local_provider: TranscriptionProvider | None = None
	cloud_provider: TranscriptionProvider | None = None

	def _get_local(self) -> TranscriptionProvider:
		if self.local_provider is None:
			self.local_provider = FasterWhisperProvider(self.config)
		return self.local_provider

	def _get_cloud(self) -> TranscriptionProvider:
		if self.cloud_provider is None:
			self.cloud_provider = OpenAIWhisperProvider(self.config)
		return self.cloud_provider

	def _run_with_timeout(self, func, *, timeout: int):
		with concurrent.futures.ThreadPoolExecutor(max_workers=1) as ex:
			fut = ex.submit(func)
			return fut.result(timeout=timeout)

	def _call_provider_with_timeout(self, provider: TranscriptionProvider, wav: Path, timeout: int):
		return self._run_with_timeout(lambda: provider.transcribe(wav), timeout=timeout)

	def transcribe(self, src_audio_path: Path) -> TranscriptionResult:
		"""Convert to wav 16k mono, optionally chunk, then transcribe via selected provider.

		Fallback: if default provider fails or times out, and fallback=cloud -> try cloud.
		"""
		logger.info(f"Starting transcription for: {src_audio_path.name}")
		
		# Normalize to wav 16k mono
		wav = ensure_wav_16k_mono(
			src_audio_path, config=self.config, dst_dir=Path(self.config.paths.cache_dir)
		)
		logger.debug(f"Normalized audio to: {wav}")

		# Cache check (by normalized wav bytes)
		storage = Storage(self.config)
		file_hash = sha256_of_file(wav)
		cached = storage.get_transcript(file_hash)
		if cached:
			provider = cached.get('provider')
			logger.info(f"Cache hit for hash: {file_hash[:8]}... (provider: {provider})")
			return TranscriptionResult(
				text=cached["text"],
				language=cached.get("language"),
				segments=[],
				provider=f'cache:{cached.get("provider","")}',
			)
		
		logger.debug(f"Cache miss for hash: {file_hash[:8]}...")

		# Optional chunking by duration
		chunks = segment_wav_by_time(
			wav,
			max_sec=self.config.chunk.max_sec,
			output_dir=Path(self.config.paths.cache_dir) / (wav.stem + "_chunks"),
			ffmpeg_bin=self.config.paths.ffmpeg_bin,
		)
		logger.debug(f"Audio split into {len(chunks)} chunk(s)")

		def transcribe_all(provider: TranscriptionProvider) -> TranscriptionResult:
			all_segments: list[TranscriptionSegment] = []
			all_text_parts: list[str] = []
			language: str | None = None
			offset = 0.0
			for ch in chunks:
				res = provider.transcribe(ch)
				if language is None and res.language:
					language = res.language
				# Offset segments to original timeline
				for s in res.segments or []:
					all_segments.append(
						TranscriptionSegment(
							start=s.start + offset, end=s.end + offset, text=s.text
						)
					)
				if res.text:
					# separate chunks by space
					all_text_parts.append(res.text.strip())
				# update offset using last segment if present
				if res.segments:
					offset = all_segments[-1].end
				else:
					# fallback to rough estimation: average duration per chunk
					offset += self.config.chunk.max_sec
			text = " ".join(t for t in all_text_parts if t)
			return TranscriptionResult(
				text=text, language=language, segments=all_segments, provider=""
			)

		def try_with(provider_name: str) -> TranscriptionResult:
			if provider_name == "local":
				prov = self._get_local()
				timeout = self.config.timeouts.local_sec
			else:
				prov = self._get_cloud()
				timeout = self.config.timeouts.cloud_sec
			
			logger.info(f"Transcribing with {provider_name} provider (timeout: {timeout}s)")
			# run the transcription (possibly long) with timeout protection
			res = self._run_with_timeout(lambda: transcribe_all(prov), timeout=timeout)
			# fill provider name on result
			if provider_name == "cloud":
				res.provider = prov.config.cloud.model
			else:
				res.provider = "local:faster-whisper"
			logger.info(f"Transcription completed with {provider_name} provider")
			return res

		default_p = self.config.provider.default
		try:
			result = try_with(default_p)
		except Exception as e:
			logger.warning(f"Provider {default_p} failed: {e}")
			if self.config.provider.fallback == "cloud" and default_p != "cloud":
				logger.info("Attempting fallback to cloud provider")
				result = try_with("cloud")
			else:
				logger.error("Transcription failed with no fallback available")
				raise

		# Save to cache
		storage.save_transcript(
			file_hash=file_hash,
			language=result.language,
			text=result.text,
			provider=result.provider,
		)
		logger.info(
			f"Transcription saved to cache. Language: {result.language}, "
			f"Text length: {len(result.text)} chars"
		)
		return result


