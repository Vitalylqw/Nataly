from __future__ import annotations

import json
import logging
from pathlib import Path

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Document, Message

from src.core.config import AppConfig
from src.core.storage import Storage
from src.transcription.audio_io import safe_stem
from src.transcription.router import TranscriptionRouter

logger = logging.getLogger(__name__)


def get_router(*, config: AppConfig, storage: Storage) -> Router:
	"""Build and return the main bot router."""
	router = Router(name="root")
	tr_router = TranscriptionRouter(config=config)

	async def _download_by_file_id(bot: Bot, file_id: str, dest: Path) -> None:
		file = await bot.get_file(file_id)
		dest.parent.mkdir(parents=True, exist_ok=True)
		await bot.download_file(file.file_path, destination=dest)

	async def _save_response(
		message: Message, response_text: str, response_type: str = "text"
	) -> None:
		"""Save bot response to database."""
		try:
			user_id = str(message.from_user.id) if message.from_user else "unknown"
			chat_id = str(message.chat.id) if message.chat else "unknown"
			message_id = message.message_id
			storage.save_bot_response(
				message_id=message_id,
				user_id=user_id,
				chat_id=chat_id,
				response_type=response_type,
				content=response_text,
			)
		except Exception as exc:
			logger.error(f"Error saving bot response: {exc}", exc_info=True)

	async def _handle_audio(message: Message, bot: Bot, *, file_id: str, filename: str) -> None:
		user_id = str(message.from_user.id) if message.from_user else "unknown"
		chat_id = str(message.chat.id) if message.chat else "unknown"
		message_id = message.message_id
		
		logger.info(f"Received audio from user {user_id}: {filename}")
		
		# Save transcription start event
		try:
			storage.save_event(
				message_id=message_id,
				user_id=user_id,
				event_type="transcription_start",
				details=json.dumps({"filename": filename, "file_id": file_id}),
			)
		except Exception as exc:
			logger.error(f"Error saving transcription_start event: {exc}", exc_info=True)
		
		inbox_dir = Path(config.paths.inbox_dir)
		stem = safe_stem(filename)
		src_path = inbox_dir / f"{stem}"
		# keep original extension if possible
		if "." in filename:
			src_path = src_path.with_suffix("." + filename.rsplit(".", 1)[-1])
		
		logger.debug(f"Downloading file {file_id} to {src_path}")
		await _download_by_file_id(bot, file_id, src_path)

		processing_msg = "Обрабатываю аудио…"
		await message.answer(processing_msg)
		await _save_response(message, processing_msg, response_type="processing")
		
		try:
			res = tr_router.transcribe(src_path, message_id=message_id, user_id=user_id)
			text = res.text or "(пусто)"
			logger.info(
				f"Transcription successful for user {user_id}. "
				f"Provider: {res.provider}, Language: {res.language}, Length: {len(text)} chars"
			)
			
			# Save transcription success event
			try:
				storage.save_event(
					message_id=message_id,
					user_id=user_id,
					event_type="transcription_success",
					details=json.dumps({
						"provider": res.provider,
						"language": res.language,
						"text_length": len(text),
					}),
				)
			except Exception as exc:
				logger.error(f"Error saving transcription_success event: {exc}", exc_info=True)
			
			# Telegram message limit ~4096 chars; send by chunks
			prefix = "Расшифровка звуковго файла: \n"
			chunk_size = 3500 - len(prefix)
			for i in range(0, len(text), chunk_size):
				chunk = text[i : i + chunk_size]
				if i == 0:
					response_text = f"{prefix}'{chunk}'"
				else:
					response_text = chunk
				await message.answer(response_text)
				await _save_response(message, response_text, response_type="text")
		except Exception as exc:
			logger.error(f"Transcription failed for user {user_id}: {exc}", exc_info=True)
			
			# Save transcription error event
			try:
				storage.save_event(
					message_id=message_id,
					user_id=user_id,
					event_type="transcription_error",
					details=json.dumps({"error": str(exc)}),
				)
			except Exception as save_exc:
				logger.error(f"Error saving transcription_error event: {save_exc}", exc_info=True)
			
			error_msg = f"Ошибка обработки: {exc}"
			await message.answer(error_msg)
			await _save_response(message, error_msg, response_type="error")

	@router.message(Command("start"))
	async def cmd_start(message: Message) -> None:
		user_id = str(message.from_user.id) if message.from_user else "unknown"
		message_id = message.message_id
		logger.info(f"User {user_id} started bot")
		
		# Save command event
		try:
			storage.save_event(
				message_id=message_id,
				user_id=user_id,
				event_type="command_start",
			)
		except Exception as exc:
			logger.error(f"Error saving command_start event: {exc}", exc_info=True)
		
		response_text = (
			"👋 Привет! Отправьте голос или аудиофайл — верну текст.\n"
			"/help — помощь, /settings — настройки"
		)
		await message.answer(response_text)
		await _save_response(message, response_text)

	@router.message(Command("help"))
	async def cmd_help(message: Message) -> None:
		user_id = str(message.from_user.id) if message.from_user else "unknown"
		message_id = message.message_id
		
		# Save command event
		try:
			storage.save_event(
				message_id=message_id,
				user_id=user_id,
				event_type="command_help",
			)
		except Exception as exc:
			logger.error(f"Error saving command_help event: {exc}", exc_info=True)
		
		response_text = (
			"Отправьте voice, аудио (ogg/mp3/m4a/wav/webm/flac) или video note.\n"
			"Я определю язык и верну транскрипт.\n"
			"По умолчанию использую локальную модель, при ошибках — резерв OpenAI."
		)
		await message.answer(response_text)
		await _save_response(message, response_text)

	@router.message(Command("settings"))
	async def cmd_settings(message: Message) -> None:
		user_id = str(message.from_user.id) if message.from_user else "unknown"
		message_id = message.message_id
		
		# Save command event
		try:
			storage.save_event(
				message_id=message_id,
				user_id=user_id,
				event_type="command_settings",
			)
		except Exception as exc:
			logger.error(f"Error saving command_settings event: {exc}", exc_info=True)
		
		response_text = (
			"Настройки будут добавлены на следующем этапе (выбор провайдера/языка/режима)."
		)
		await message.answer(response_text)
		await _save_response(message, response_text)

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
		
		# Handle non-audio messages
		response_text = "Ожидается звуковой файл или сообщение голосом"
		await message.answer(response_text)
		await _save_response(message, response_text, response_type="info")

	def _is_audio_document(doc: Document) -> bool:
		if doc.mime_type and doc.mime_type.startswith("audio/"):
			return True
		if doc.file_name:
			ext = doc.file_name.lower().rsplit(".", 1)[-1] if "." in doc.file_name else ""
			return ext in set(config.audio.formats)
		return False

	return router


