from __future__ import annotations

import sqlite3
from dataclasses import dataclass
from pathlib import Path

from src.core.config import AppConfig


@dataclass
class Storage:
	config: AppConfig

	def _connect(self) -> sqlite3.Connection:
		conn = sqlite3.connect(self.config.paths.db_path)
		conn.row_factory = sqlite3.Row
		return conn

	def ensure_runtime_dirs(self) -> None:
		for path in [
			Path(self.config.paths.base_dir),
			Path(self.config.paths.inbox_dir),
			Path(self.config.paths.cache_dir),
			Path(self.config.paths.out_dir),
			Path(self.config.paths.db_path).parent,
		]:
			path.mkdir(parents=True, exist_ok=True)

	def init_db(self) -> None:
		with self._connect() as conn:
			# Existing tables
			conn.execute(
				"""
				CREATE TABLE IF NOT EXISTS transcripts (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					file_hash TEXT UNIQUE NOT NULL,
					language TEXT,
					text TEXT NOT NULL,
					provider TEXT NOT NULL,
					message_id INTEGER,
					user_id TEXT,
					created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
				)
				"""
			)
			conn.execute(
				"""
				CREATE TABLE IF NOT EXISTS user_settings (
					user_id TEXT PRIMARY KEY,
					provider TEXT,
					language TEXT,
					mode TEXT
				)
				"""
			)
			
			# New tables for message logging
			conn.execute(
				"""
				CREATE TABLE IF NOT EXISTS messages (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					message_id INTEGER NOT NULL,
					user_id TEXT NOT NULL,
					chat_id TEXT NOT NULL,
					message_type TEXT NOT NULL,
					content TEXT,
					file_id TEXT,
					file_unique_id TEXT,
					filename TEXT,
					mime_type TEXT,
					created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
					UNIQUE(message_id, chat_id)
				)
				"""
			)
			conn.execute(
				"""
				CREATE TABLE IF NOT EXISTS bot_responses (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					message_id INTEGER,
					user_id TEXT NOT NULL,
					chat_id TEXT NOT NULL,
					response_type TEXT NOT NULL,
					content TEXT NOT NULL,
					created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
				)
				"""
			)
			conn.execute(
				"""
				CREATE TABLE IF NOT EXISTS events (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					message_id INTEGER,
					user_id TEXT NOT NULL,
					event_type TEXT NOT NULL,
					details TEXT,
					created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
				)
				"""
			)
			
			# Migrate existing transcripts table if needed
			try:
				cursor = conn.execute("PRAGMA table_info(transcripts)")
				columns = [row[1] for row in cursor.fetchall()]
				if "message_id" not in columns:
					conn.execute("ALTER TABLE transcripts ADD COLUMN message_id INTEGER")
				if "user_id" not in columns:
					conn.execute("ALTER TABLE transcripts ADD COLUMN user_id TEXT")
			except sqlite3.Error:
				pass  # Table might not exist yet, will be created above
			
			# Create indexes for performance
			conn.execute(
				"CREATE INDEX IF NOT EXISTS idx_messages_user_id ON messages(user_id)"
			)
			conn.execute(
				"CREATE INDEX IF NOT EXISTS idx_messages_created_at ON messages(created_at)"
			)
			conn.execute(
				"CREATE INDEX IF NOT EXISTS idx_bot_responses_message_id ON bot_responses(message_id)"
			)
			conn.execute(
				"CREATE INDEX IF NOT EXISTS idx_bot_responses_user_id ON bot_responses(user_id)"
			)
			conn.execute(
				"CREATE INDEX IF NOT EXISTS idx_events_user_id ON events(user_id)"
			)
			conn.execute(
				"CREATE INDEX IF NOT EXISTS idx_events_event_type ON events(event_type)"
			)
			conn.execute(
				"CREATE INDEX IF NOT EXISTS idx_transcripts_user_id ON transcripts(user_id)"
			)

	def get_transcript(self, file_hash: str) -> dict | None:
		with self._connect() as conn:
			row = conn.execute(
				"SELECT file_hash, language, text, provider, message_id, user_id, created_at "
				"FROM transcripts WHERE file_hash=?",
				(file_hash,),
			).fetchone()
			return dict(row) if row else None

	def save_transcript(
		self,
		*,
		file_hash: str,
		language: str | None,
		text: str,
		provider: str,
		message_id: int | None = None,
		user_id: str | None = None,
	) -> None:
		with self._connect() as conn:
			conn.execute(
				"""
				INSERT INTO transcripts (file_hash, language, text, provider, message_id, user_id)
				VALUES (?, ?, ?, ?, ?, ?)
				ON CONFLICT(file_hash) DO UPDATE SET
					language=excluded.language,
					text=excluded.text,
					provider=excluded.provider,
					message_id=COALESCE(excluded.message_id, transcripts.message_id),
					user_id=COALESCE(excluded.user_id, transcripts.user_id)
				""",
				(file_hash, language, text, provider, message_id, user_id),
			)

	def get_user_settings(self, user_id: str) -> dict | None:
		with self._connect() as conn:
			row = conn.execute(
				"SELECT user_id, provider, language, mode FROM user_settings WHERE user_id=?",
				(user_id,),
			).fetchone()
			return dict(row) if row else None

	def upsert_user_settings(
		self,
		*,
		user_id: str,
		provider: str | None = None,
		language: str | None = None,
		mode: str | None = None,
	) -> None:
		with self._connect() as conn:
			conn.execute(
				"""
				INSERT INTO user_settings (user_id, provider, language, mode)
				VALUES (?, ?, ?, ?)
				ON CONFLICT(user_id) DO UPDATE SET
					provider=COALESCE(excluded.provider, user_settings.provider),
					language=COALESCE(excluded.language, user_settings.language),
					mode=COALESCE(excluded.mode, user_settings.mode)
				""",
				(user_id, provider, language, mode),
			)

	def save_message(
		self,
		*,
		message_id: int,
		user_id: str,
		chat_id: str,
		message_type: str,
		content: str | None = None,
		file_id: str | None = None,
		file_unique_id: str | None = None,
		filename: str | None = None,
		mime_type: str | None = None,
	) -> None:
		"""Save incoming message to database."""
		with self._connect() as conn:
			conn.execute(
				"""
				INSERT INTO messages (
					message_id, user_id, chat_id, message_type,
					content, file_id, file_unique_id, filename, mime_type
				)
				VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
				ON CONFLICT(message_id, chat_id) DO UPDATE SET
					content=excluded.content,
					file_id=excluded.file_id,
					file_unique_id=excluded.file_unique_id,
					filename=excluded.filename,
					mime_type=excluded.mime_type
				""",
				(
					message_id,
					user_id,
					chat_id,
					message_type,
					content,
					file_id,
					file_unique_id,
					filename,
					mime_type,
				),
			)

	def save_bot_response(
		self,
		*,
		message_id: int | None,
		user_id: str,
		chat_id: str,
		response_type: str,
		content: str,
	) -> None:
		"""Save bot response to database."""
		with self._connect() as conn:
			conn.execute(
				"""
				INSERT INTO bot_responses (
					message_id, user_id, chat_id, response_type, content
				)
				VALUES (?, ?, ?, ?, ?)
				""",
				(message_id, user_id, chat_id, response_type, content),
			)

	def save_event(
		self,
		*,
		message_id: int | None,
		user_id: str,
		event_type: str,
		details: str | None = None,
	) -> None:
		"""Save event/action to database."""
		with self._connect() as conn:
			conn.execute(
				"""
				INSERT INTO events (message_id, user_id, event_type, details)
				VALUES (?, ?, ?, ?)
				""",
				(message_id, user_id, event_type, details),
			)

	def get_message_by_id(self, message_id: int, chat_id: str) -> dict | None:
		"""Get message by message_id and chat_id."""
		with self._connect() as conn:
			row = conn.execute(
				"""
				SELECT id, message_id, user_id, chat_id, message_type,
				       content, file_id, file_unique_id, filename, mime_type, created_at
				FROM messages
				WHERE message_id=? AND chat_id=?
				""",
				(message_id, chat_id),
			).fetchone()
			return dict(row) if row else None

	def get_user_messages(
		self, user_id: str, limit: int = 100, offset: int = 0
	) -> list[dict]:
		"""Get user messages ordered by created_at DESC."""
		with self._connect() as conn:
			rows = conn.execute(
				"""
				SELECT id, message_id, user_id, chat_id, message_type,
				       content, file_id, file_unique_id, filename, mime_type, created_at
				FROM messages
				WHERE user_id=?
				ORDER BY created_at DESC
				LIMIT ? OFFSET ?
				""",
				(user_id, limit, offset),
			).fetchall()
			return [dict(row) for row in rows]

	def get_user_responses(
		self, user_id: str, limit: int = 100, offset: int = 0
	) -> list[dict]:
		"""Get bot responses for user ordered by created_at DESC."""
		with self._connect() as conn:
			rows = conn.execute(
				"""
				SELECT id, message_id, user_id, chat_id, response_type, content, created_at
				FROM bot_responses
				WHERE user_id=?
				ORDER BY created_at DESC
				LIMIT ? OFFSET ?
				""",
				(user_id, limit, offset),
			).fetchall()
			return [dict(row) for row in rows]

	def get_user_events(
		self, user_id: str, event_type: str | None = None, limit: int = 100, offset: int = 0
	) -> list[dict]:
		"""Get user events ordered by created_at DESC."""
		with self._connect() as conn:
			if event_type:
				rows = conn.execute(
					"""
					SELECT id, message_id, user_id, event_type, details, created_at
					FROM events
					WHERE user_id=? AND event_type=?
					ORDER BY created_at DESC
					LIMIT ? OFFSET ?
					""",
					(user_id, event_type, limit, offset),
				).fetchall()
			else:
				rows = conn.execute(
					"""
					SELECT id, message_id, user_id, event_type, details, created_at
					FROM events
					WHERE user_id=?
					ORDER BY created_at DESC
					LIMIT ? OFFSET ?
					""",
					(user_id, limit, offset),
				).fetchall()
			return [dict(row) for row in rows]


