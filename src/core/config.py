from __future__ import annotations

import os
from pathlib import Path
from typing import Literal

import yaml
from dotenv import load_dotenv
from pydantic import BaseModel, Field


class ProviderSelection(BaseModel):
	default: Literal["local", "cloud"] = "local"
	fallback: Literal["cloud", "none"] = "cloud"


class LocalConfig(BaseModel):
	model: str = "large-v3"
	device: Literal["cuda", "cpu", "auto"] = "cuda"
	compute_type: Literal["float16", "int8_float16", "float32"] = "float16"
	beam_size: int = 5


class CloudConfig(BaseModel):
	provider: Literal["openai"] = "openai"
	model: str = "gpt-4o-mini-transcribe"


class AudioConfig(BaseModel):
	sample_rate: int = 16000
	channels: int = 1
	formats: list[str] = Field(
		default_factory=lambda: ["ogg", "opus", "oga", "mp3", "m4a", "wav", "webm", "flac"]
	)


class ChunkConfig(BaseModel):
	max_sec: int = 90


class Timeouts(BaseModel):
	local_sec: int = 180
	cloud_sec: int = 180


class Paths(BaseModel):
	ffmpeg_bin: str | None = None
	base_dir: str = "var"
	inbox_dir: str = "var/inbox"
	cache_dir: str = "var/cache"
	out_dir: str = "var/out"
	db_path: str = "var/app.db"
	model_dir: str = "var/models"


class AppConfig(BaseModel):
	telegram_token: str = ""
	openai_api_key: str = ""
	env: Literal["dev", "prod", "test"] = "dev"

	provider: ProviderSelection = ProviderSelection()
	local: LocalConfig = LocalConfig()
	cloud: CloudConfig = CloudConfig()
	audio: AudioConfig = AudioConfig()
	chunk: ChunkConfig = ChunkConfig()
	timeouts: Timeouts = Timeouts()
	paths: Paths = Paths()


def _load_settings_yaml(path: Path) -> dict:
	if not path.exists():
		return {}
	with path.open("r", encoding="utf-8") as f:
		return yaml.safe_load(f) or {}


def load_config() -> AppConfig:
	"""Load configuration from .env and settings.yaml, merge and validate."""
	load_dotenv()

	root = Path(__file__).resolve().parents[1]
	default_settings_path = root / "config" / "settings.yaml"
	settings_path = Path(os.getenv("SETTINGS_FILE") or default_settings_path)

	data = _load_settings_yaml(settings_path)
	cfg = AppConfig.model_validate(data or {})

	# .env overrides
	cfg.telegram_token = os.getenv("TELEGRAM_TOKEN", cfg.telegram_token)
	cfg.openai_api_key = os.getenv("OPENAI_API_KEY", cfg.openai_api_key)
	cfg.env = os.getenv("ENV", cfg.env)  # type: ignore[assignment]

	provider_default = os.getenv("PROVIDER_DEFAULT")
	provider_fallback = os.getenv("PROVIDER_FALLBACK")
	if provider_default in {"local", "cloud"}:
		cfg.provider.default = provider_default  # type: ignore[assignment]
	if provider_fallback in {"cloud", "none"}:
		cfg.provider.fallback = provider_fallback  # type: ignore[assignment]

	# Ensure runtime dirs exist
	base = Path(cfg.paths.base_dir)
	for sub in [
		base,
		Path(cfg.paths.inbox_dir),
		Path(cfg.paths.cache_dir),
		Path(cfg.paths.out_dir),
		Path(cfg.paths.model_dir),
		Path(Path(cfg.paths.db_path).parent),
	]:
		sub.mkdir(parents=True, exist_ok=True)

	return cfg


