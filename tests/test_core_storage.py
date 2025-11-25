from __future__ import annotations

from pathlib import Path

from src.core.config import AppConfig, Paths
from src.core.storage import Storage


def _make_storage(tmp_path: Path) -> Storage:
	base = tmp_path / "var"
	paths = Paths(
		ffmpeg_bin=None,
		base_dir=str(base),
		inbox_dir=str(base / "inbox"),
		cache_dir=str(base / "cache"),
		out_dir=str(base / "out"),
		db_path=str(base / "db" / "app.db"),
	)
	cfg = AppConfig(paths=paths)
	storage = Storage(cfg)
	storage.ensure_runtime_dirs()
	storage.init_db()
	return storage


def test_storage_transcript_upsert(tmp_path):
	storage = _make_storage(tmp_path)
	file_hash = "abc123"

	storage.save_transcript(file_hash=file_hash, language="en", text="hello", provider="local")
	row = storage.get_transcript(file_hash)
	assert row is not None
	assert row["text"] == "hello"
	assert row["language"] == "en"
	assert row["provider"] == "local"

	storage.save_transcript(file_hash=file_hash, language="de", text="updated", provider="cloud")
	row = storage.get_transcript(file_hash)
	assert row is not None
	assert row["text"] == "updated"
	assert row["language"] == "de"
	assert row["provider"] == "cloud"


def test_storage_user_settings_upsert(tmp_path):
	storage = _make_storage(tmp_path)

	storage.upsert_user_settings(user_id="u1", provider="local", language="ru", mode="voice")
	row = storage.get_user_settings("u1")
	assert row is not None
	assert row["provider"] == "local"
	assert row["language"] == "ru"
	assert row["mode"] == "voice"

	# Only language changes, provider/mode stay the same
	storage.upsert_user_settings(user_id="u1", language="en")
	row = storage.get_user_settings("u1")
	assert row is not None
	assert row["provider"] == "local"
	assert row["language"] == "en"
	assert row["mode"] == "voice"

