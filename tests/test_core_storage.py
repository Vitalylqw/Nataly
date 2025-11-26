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


def test_storage_save_message(tmp_path):
	storage = _make_storage(tmp_path)
	
	storage.save_message(
		message_id=123,
		user_id="u1",
		chat_id="c1",
		message_type="text",
		content="Hello",
	)
	
	msg = storage.get_message_by_id(message_id=123, chat_id="c1")
	assert msg is not None
	assert msg["message_id"] == 123
	assert msg["user_id"] == "u1"
	assert msg["chat_id"] == "c1"
	assert msg["message_type"] == "text"
	assert msg["content"] == "Hello"


def test_storage_save_message_with_file(tmp_path):
	storage = _make_storage(tmp_path)
	
	storage.save_message(
		message_id=456,
		user_id="u2",
		chat_id="c1",
		message_type="voice",
		file_id="file123",
		file_unique_id="unique123",
		filename="voice.ogg",
		mime_type="audio/ogg",
	)
	
	msg = storage.get_message_by_id(message_id=456, chat_id="c1")
	assert msg is not None
	assert msg["message_type"] == "voice"
	assert msg["file_id"] == "file123"
	assert msg["file_unique_id"] == "unique123"
	assert msg["filename"] == "voice.ogg"
	assert msg["mime_type"] == "audio/ogg"


def test_storage_save_bot_response(tmp_path):
	storage = _make_storage(tmp_path)
	
	storage.save_bot_response(
		message_id=123,
		user_id="u1",
		chat_id="c1",
		response_type="text",
		content="Response text",
	)
	
	responses = storage.get_user_responses(user_id="u1", limit=10)
	assert len(responses) == 1
	assert responses[0]["message_id"] == 123
	assert responses[0]["response_type"] == "text"
	assert responses[0]["content"] == "Response text"


def test_storage_save_event(tmp_path):
	storage = _make_storage(tmp_path)
	
	storage.save_event(
		message_id=123,
		user_id="u1",
		event_type="command_start",
	)
	
	events = storage.get_user_events(user_id="u1", limit=10)
	assert len(events) == 1
	assert events[0]["message_id"] == 123
	assert events[0]["event_type"] == "command_start"
	assert events[0]["details"] is None


def test_storage_save_event_with_details(tmp_path):
	storage = _make_storage(tmp_path)
	
	storage.save_event(
		message_id=456,
		user_id="u2",
		event_type="transcription_success",
		details='{"provider": "local", "language": "en"}',
	)
	
	events = storage.get_user_events(user_id="u2", event_type="transcription_success", limit=10)
	assert len(events) == 1
	assert events[0]["event_type"] == "transcription_success"
	assert events[0]["details"] == '{"provider": "local", "language": "en"}'


def test_storage_get_user_messages(tmp_path):
	storage = _make_storage(tmp_path)
	
	# Save multiple messages
	for i in range(5):
		storage.save_message(
			message_id=100 + i,
			user_id="u1",
			chat_id="c1",
			message_type="text",
			content=f"Message {i}",
		)
	
	messages = storage.get_user_messages(user_id="u1", limit=10)
	assert len(messages) == 5
	# Check that we have all messages
	message_ids = {msg["message_id"] for msg in messages}
	assert message_ids == {100, 101, 102, 103, 104}
	# Verify all messages have correct structure
	for msg in messages:
		assert msg["user_id"] == "u1"
		assert msg["chat_id"] == "c1"
		assert msg["message_type"] == "text"


def test_storage_transcript_with_message_id(tmp_path):
	storage = _make_storage(tmp_path)
	
	storage.save_transcript(
		file_hash="hash123",
		language="en",
		text="transcript text",
		provider="local",
		message_id=789,
		user_id="u1",
	)
	
	row = storage.get_transcript("hash123")
	assert row is not None
	assert row["message_id"] == 789
	assert row["user_id"] == "u1"