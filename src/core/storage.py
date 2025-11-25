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
			conn.execute(
				"""
				CREATE TABLE IF NOT EXISTS transcripts (
					id INTEGER PRIMARY KEY AUTOINCREMENT,
					file_hash TEXT UNIQUE NOT NULL,
					language TEXT,
					text TEXT NOT NULL,
					provider TEXT NOT NULL,
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

	def get_transcript(self, file_hash: str) -> dict | None:
		with self._connect() as conn:
			row = conn.execute(
				"SELECT file_hash, language, text, provider, created_at "
				"FROM transcripts WHERE file_hash=?",
				(file_hash,),
			).fetchone()
			return dict(row) if row else None

	def save_transcript(
		self, *, file_hash: str, language: str | None, text: str, provider: str
	) -> None:
		with self._connect() as conn:
			conn.execute(
				"""
				INSERT INTO transcripts (file_hash, language, text, provider)
				VALUES (?, ?, ?, ?)
				ON CONFLICT(file_hash) DO UPDATE SET
					language=excluded.language,
					text=excluded.text,
					provider=excluded.provider
				""",
				(file_hash, language, text, provider),
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


