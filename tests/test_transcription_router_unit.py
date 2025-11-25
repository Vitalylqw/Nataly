from __future__ import annotations

from pathlib import Path
from types import SimpleNamespace

import pytest

from src.core.config import AppConfig, ChunkConfig, Paths, ProviderSelection, Timeouts
from src.core.storage import Storage
from src.domain.models import TranscriptionResult, TranscriptionSegment
from src.transcription.router import TranscriptionRouter
from src.utils.hashing import sha256_of_file


def _make_config(tmp_path: Path, *, fallback: str = "cloud") -> AppConfig:
	base = tmp_path / "var"
	return AppConfig(
		provider=ProviderSelection(default="local", fallback=fallback),
		chunk=ChunkConfig(max_sec=5),
		timeouts=Timeouts(local_sec=1, cloud_sec=1),
		paths=Paths(
			ffmpeg_bin=None,
			base_dir=str(base),
			inbox_dir=str(base / "inbox"),
			cache_dir=str(base / "cache"),
			out_dir=str(base / "out"),
			db_path=str(base / "db" / "app.db"),
		),
	)


def _prepare_storage(cfg: AppConfig) -> Storage:
	storage = Storage(cfg)
	storage.ensure_runtime_dirs()
	storage.init_db()
	return storage


def test_transcription_router_returns_cached_result(tmp_path, monkeypatch):
	cfg = _make_config(tmp_path)
	storage = _prepare_storage(cfg)

	src_audio = tmp_path / "audio.ogg"
	src_audio.write_bytes(b"original")
	norm_wav = Path(cfg.paths.cache_dir) / "audio_16k_mono.wav"
	norm_wav.parent.mkdir(parents=True, exist_ok=True)
	norm_wav.write_bytes(b"normalized")

	monkeypatch.setattr(
		"src.transcription.router.ensure_wav_16k_mono",
		lambda *_args, **_kwargs: norm_wav,
	)
	monkeypatch.setattr(
		"src.transcription.router.segment_wav_by_time",
		lambda *_args, **_kwargs: [norm_wav],
	)

	file_hash = sha256_of_file(norm_wav)
	storage.save_transcript(
		file_hash=file_hash,
		language="en",
		text="cached text",
		provider="local",
	)

	router = TranscriptionRouter(config=cfg)
	result = router.transcribe(src_audio)

	assert result.text == "cached text"
	assert result.language == "en"
	assert result.provider.startswith("cache:")


def test_transcription_router_fallback_to_cloud_on_error(tmp_path, monkeypatch):
	cfg = _make_config(tmp_path)
	cfg.cloud.model = "gpt-test"
	storage = _prepare_storage(cfg)

	src_audio = tmp_path / "speech.mp3"
	src_audio.write_bytes(b"src")
	norm_wav = Path(cfg.paths.cache_dir) / "speech_16k_mono.wav"
	norm_wav.parent.mkdir(parents=True, exist_ok=True)
	norm_wav.write_bytes(b"norm")
	chunk = tmp_path / "chunk_000.wav"
	chunk.write_bytes(b"chunk")

	monkeypatch.setattr(
		"src.transcription.router.ensure_wav_16k_mono",
		lambda *_args, **_kwargs: norm_wav,
	)
	monkeypatch.setattr(
		"src.transcription.router.segment_wav_by_time",
		lambda *_args, **_kwargs: [chunk],
	)

	def immediate(self, func, *, timeout):
		return func()

	monkeypatch.setattr(TranscriptionRouter, "_run_with_timeout", immediate)

	class FailingProvider:
		def transcribe(self, _wav_path):
			raise RuntimeError("fail")

	class CloudProvider:
		def __init__(self):
			self.config = SimpleNamespace(cloud=SimpleNamespace(model="gpt-test"))

		def transcribe(self, _wav_path):
			segment = TranscriptionSegment(start=0.0, end=1.0, text="cloud")
			return TranscriptionResult(
				text="cloud text",
				language="en",
				segments=[segment],
				provider="",
			)

	failing_provider = FailingProvider()
	cloud_provider = CloudProvider()

	monkeypatch.setattr(TranscriptionRouter, "_get_local", lambda self: failing_provider)
	monkeypatch.setattr(TranscriptionRouter, "_get_cloud", lambda self: cloud_provider)

	router = TranscriptionRouter(config=cfg)
	result = router.transcribe(src_audio)

	assert result.text == "cloud text"
	assert result.provider == "gpt-test"
	assert result.language == "en"

	file_hash = sha256_of_file(norm_wav)
	stored = storage.get_transcript(file_hash)
	assert stored is not None
	assert stored["text"] == "cloud text"
	assert stored["provider"] == "gpt-test"


def test_transcription_router_merges_chunk_segments(tmp_path, monkeypatch):
	cfg = _make_config(tmp_path, fallback="none")
	storage = _prepare_storage(cfg)

	src_audio = tmp_path / "multi.wav"
	src_audio.write_bytes(b"src")
	norm_wav = Path(cfg.paths.cache_dir) / "multi_16k_mono.wav"
	norm_wav.parent.mkdir(parents=True, exist_ok=True)
	norm_wav.write_bytes(b"norm")
	chunk_a = tmp_path / "chunk_a.wav"
	chunk_b = tmp_path / "chunk_b.wav"
	chunk_a.write_bytes(b"a")
	chunk_b.write_bytes(b"b")

	monkeypatch.setattr(
		"src.transcription.router.ensure_wav_16k_mono",
		lambda *_args, **_kwargs: norm_wav,
	)
	monkeypatch.setattr(
		"src.transcription.router.segment_wav_by_time",
		lambda *_args, **_kwargs: [chunk_a, chunk_b],
	)
	monkeypatch.setattr(
		TranscriptionRouter,
		"_run_with_timeout",
		lambda self, func, *, timeout: func(),
	)

	class MappingProvider:
		def __init__(self, mapping):
			self.mapping = mapping

		def transcribe(self, wav_path):
			return self.mapping[wav_path]

	provider = MappingProvider(
		{
			chunk_a: TranscriptionResult(
				text=" hello ",
				language="en",
				segments=[TranscriptionSegment(start=0.0, end=1.5, text="hello")],
				provider="",
			),
			chunk_b: TranscriptionResult(
				text="world ",
				language=None,
				segments=[TranscriptionSegment(start=0.0, end=2.0, text="world")],
				provider="",
			),
		}
	)

	monkeypatch.setattr(TranscriptionRouter, "_get_local", lambda self: provider)

	router = TranscriptionRouter(config=cfg)
	result = router.transcribe(src_audio)

	assert result.text == "hello world"
	assert result.language == "en"
	assert len(result.segments) == 2
	assert result.segments[0].start == pytest.approx(0.0)
	assert result.segments[0].end == pytest.approx(1.5)
	assert result.segments[1].start == pytest.approx(1.5)
	assert result.segments[1].end == pytest.approx(3.5)

	file_hash = sha256_of_file(norm_wav)
	stored = storage.get_transcript(file_hash)
	assert stored is not None
	assert stored["text"] == "hello world"

