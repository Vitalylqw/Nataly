from __future__ import annotations

import logging
from pathlib import Path

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Document, Message

from src.core.config import AppConfig
from src.transcription.audio_io import safe_stem
from src.transcription.router import TranscriptionRouter

logger = logging.getLogger(__name__)


def get_router(*, config: AppConfig) -> Router:
	"""Build and return the main bot router."""
	router = Router(name="root")
	tr_router = TranscriptionRouter(config=config)

	async def _download_by_file_id(bot: Bot, file_id: str, dest: Path) -> None:
		file = await bot.get_file(file_id)
		dest.parent.mkdir(parents=True, exist_ok=True)
		await bot.download_file(file.file_path, destination=dest)

	async def _handle_audio(message: Message, bot: Bot, *, file_id: str, filename: str) -> None:
		user_id = message.from_user.id if message.from_user else "unknown"
		logger.info(f"Received audio from user {user_id}: {filename}")
		
		inbox_dir = Path(config.paths.inbox_dir)
		stem = safe_stem(filename)
		src_path = inbox_dir / f"{stem}"
		# keep original extension if possible
		if "." in filename:
			src_path = src_path.with_suffix("." + filename.rsplit(".", 1)[-1])
		
		logger.debug(f"Downloading file {file_id} to {src_path}")
		await _download_by_file_id(bot, file_id, src_path)

		await message.answer("Обрабатываю аудио…")
		try:
			res = tr_router.transcribe(src_path)
			text = res.text or "(пусто)"
			logger.info(
				f"Transcription successful for user {user_id}. "
				f"Provider: {res.provider}, Language: {res.language}, Length: {len(text)} chars"
			)
			# Telegram message limit ~4096 chars; send by chunks
			for i in range(0, len(text), 3500):
				await message.answer(text[i : i + 3500])
		except Exception as exc:
			logger.error(f"Transcription failed for user {user_id}: {exc}", exc_info=True)
			await message.answer(f"Ошибка обработки: {exc}")

	@router.message(Command("start"))
	async def cmd_start(message: Message) -> None:
		user_id = message.from_user.id if message.from_user else "unknown"
		logger.info(f"User {user_id} started bot")
		await message.answer(
			"👋 Привет! Отправьте голос или аудиофайл — верну текст.\n"
			"/help — помощь, /settings — настройки"
		)

	@router.message(Command("help"))
	async def cmd_help(message: Message) -> None:
		await message.answer(
			"Отправьте voice, аудио (ogg/mp3/m4a/wav/webm/flac) или video note.\n"
			"Я определю язык и верну транскрипт.\n"
			"По умолчанию использую локальную модель, при ошибках — резерв OpenAI."
		)

	@router.message(Command("settings"))
	async def cmd_settings(message: Message) -> None:
		await message.answer(
			"Настройки будут добавлены на следующем этапе (выбор провайдера/языка/режима)."
		)

	@router.message()
	async def on_message(message: Message, bot: Bot) -> None:
		# voice
		if message.voice:
			file_id = message.voice.file_id
			filename = f"voice_{message.voice.file_unique_id}.ogg"
			return await _handle_audio(message, bot, file_id=file_id, filename=filename)
		# audio
		if message.audio:
			file_id = message.audio.file_id
			filename = message.audio.file_name or f"audio_{message.audio.file_unique_id}.mp3"
			return await _handle_audio(message, bot, file_id=file_id, filename=filename)
		# video note (circle)
		if message.video_note:
			file_id = message.video_note.file_id
			filename = f"videonote_{message.video_note.file_unique_id}.mp4"
			return await _handle_audio(message, bot, file_id=file_id, filename=filename)
		# documents that may contain audio
		if message.document and _is_audio_document(message.document):
			file_id = message.document.file_id
			filename = message.document.file_name or f"doc_{message.document.file_unique_id}"
			return await _handle_audio(message, bot, file_id=file_id, filename=filename)

	def _is_audio_document(doc: Document) -> bool:
		if doc.mime_type and doc.mime_type.startswith("audio/"):
			return True
		if doc.file_name:
			ext = doc.file_name.lower().rsplit(".", 1)[-1] if "." in doc.file_name else ""
			return ext in set(config.audio.formats)
		return False

	return router


