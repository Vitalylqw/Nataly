from __future__ import annotations

import json
import logging
from datetime import datetime
from pathlib import Path

from aiogram import Bot, Router
from aiogram.filters import Command
from aiogram.types import Document, Message

from src.core.config import AppConfig
from src.core.storage import Storage
from src.domain.models import TranscriptionResult
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

	async def _save_file_to_inbox(
		bot: Bot, file_id: str, filename: str, message_type: str = "file"
	) -> Path | None:
		"""Save any file to inbox directory.
		
		Args:
			bot: Bot instance for downloading files
			file_id: Telegram file_id
			filename: Target filename
			message_type: Type of message (for logging)
			
		Returns:
			Path to saved file or None if error occurred
		"""
		try:
			inbox_dir = Path(config.paths.inbox_dir)
			stem = safe_stem(filename)
			dest_path = inbox_dir / f"{stem}"
			# Keep original extension if possible
			if "." in filename:
				dest_path = dest_path.with_suffix("." + filename.rsplit(".", 1)[-1])
			
			# Skip if file already exists
			if dest_path.exists():
				logger.debug(f"File already exists in inbox: {dest_path}")
				return dest_path
			
			logger.debug(f"Saving {message_type} file {file_id} to {dest_path}")
			await _download_by_file_id(bot, file_id, dest_path)
			logger.info(f"Saved {message_type} file to inbox: {dest_path.name}")
			return dest_path
		except Exception as exc:
			logger.error(f"Error saving {message_type} file to inbox: {exc}", exc_info=True)
			return None

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

	async def _save_transcription_to_json(
		result: TranscriptionResult,
		*,
		filename: str,
		file_id: str,
		message_id: int,
		user_id: str,
		message_type: str = "audio",
	) -> Path | None:
		"""Save transcription result to JSON file in out directory.
		
		Args:
			result: TranscriptionResult with text, language, segments, provider
			filename: Original filename
			file_id: Telegram file_id
			message_id: Telegram message_id
			user_id: User ID
			message_type: Type of message (audio/video)
			
		Returns:
			Path to saved JSON file or None if error occurred
		"""
		try:
			out_dir = Path(config.paths.out_dir)
			stem = safe_stem(filename)
			json_path = out_dir / f"{stem}_transcript.json"
			
			# Prepare JSON data
			json_data = {
				"metadata": {
					"original_filename": filename,
					"file_id": file_id,
					"message_id": message_id,
					"user_id": user_id,
					"message_type": message_type,
					"timestamp": datetime.utcnow().isoformat() + "Z",
				},
				"transcription": {
					"text": result.text,
					"language": result.language,
					"provider": result.provider,
					"text_length": len(result.text) if result.text else 0,
					"segments_count": len(result.segments),
				},
				"segments": [
					{
						"start": seg.start,
						"end": seg.end,
						"text": seg.text,
					}
					for seg in result.segments
				],
			}
			
			# Write JSON file
			out_dir.mkdir(parents=True, exist_ok=True)
			with json_path.open("w", encoding="utf-8") as f:
				json.dump(json_data, f, ensure_ascii=False, indent=2)
			
			logger.info(f"Saved transcription JSON to {json_path.name}")
			return json_path
		except Exception as exc:
			logger.error(f"Error saving transcription JSON: {exc}", exc_info=True)
			return None

	async def _handle_audio(message: Message, bot: Bot, *, file_id: str, filename: str) -> None:
		user_id = str(message.from_user.id) if message.from_user else "unknown"
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
			
			# Save transcription to JSON file
			try:
				await _save_transcription_to_json(
					res,
					filename=filename,
					file_id=file_id,
					message_id=message_id,
					user_id=user_id,
					message_type="audio",
				)
			except Exception as exc:
				logger.error(f"Error saving transcription JSON: {exc}", exc_info=True)
			
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

	async def _handle_video(message: Message, bot: Bot, *, file_id: str, filename: str) -> None:
		"""Handle video file transcription by extracting audio track."""
		user_id = str(message.from_user.id) if message.from_user else "unknown"
		message_id = message.message_id
		
		logger.info(f"Received video from user {user_id}: {filename}")
		
		# Save transcription start event
		try:
			storage.save_event(
				message_id=message_id,
				user_id=user_id,
				event_type="transcription_start",
				details=json.dumps({"filename": filename, "file_id": file_id, "type": "video"}),
			)
		except Exception as exc:
			logger.error(f"Error saving transcription_start event: {exc}", exc_info=True)
		
		inbox_dir = Path(config.paths.inbox_dir)
		stem = safe_stem(filename)
		src_path = inbox_dir / f"{stem}"
		# keep original extension if possible
		if "." in filename:
			src_path = src_path.with_suffix("." + filename.rsplit(".", 1)[-1])
		
		logger.debug(f"Downloading video file {file_id} to {src_path}")
		await _download_by_file_id(bot, file_id, src_path)

		processing_msg = "Обрабатываю видео…"
		await message.answer(processing_msg)
		await _save_response(message, processing_msg, response_type="processing")
		
		try:
			res = tr_router.transcribe(src_path, message_id=message_id, user_id=user_id)
			text = res.text or "(пусто)"
			logger.info(
				f"Video transcription successful for user {user_id}. "
				f"Provider: {res.provider}, Language: {res.language}, Length: {len(text)} chars"
			)
			
			# Save transcription to JSON file
			try:
				await _save_transcription_to_json(
					res,
					filename=filename,
					file_id=file_id,
					message_id=message_id,
					user_id=user_id,
					message_type="video",
				)
			except Exception as exc:
				logger.error(f"Error saving transcription JSON: {exc}", exc_info=True)
			
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
						"type": "video",
					}),
				)
			except Exception as exc:
				logger.error(f"Error saving transcription_success event: {exc}", exc_info=True)
			
			# Telegram message limit ~4096 chars; send by chunks
			prefix = "Расшифровка видео: \n"
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
			logger.error(f"Video transcription failed for user {user_id}: {exc}", exc_info=True)
			
			# Save transcription error event
			try:
				storage.save_event(
					message_id=message_id,
					user_id=user_id,
					event_type="transcription_error",
					details=json.dumps({"error": str(exc), "type": "video"}),
				)
			except Exception as save_exc:
				logger.error(f"Error saving transcription_error event: {save_exc}", exc_info=True)
			
			error_msg = f"Ошибка обработки видео: {exc}"
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
			"👋 Привет! Отправьте голос, аудио или видео — верну текст.\n"
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
			"Отправьте voice, аудио (ogg/mp3/m4a/wav/webm/flac), "
			"видео (mp4/avi/mov/mkv/webm) или video note.\n"
			"Я извлеку аудиодорожку, определю язык и верну транскрипт.\n"
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
		# video
		if message.video:
			file_id = message.video.file_id
			filename = message.video.file_name or f"video_{message.video.file_unique_id}.mp4"
			return await _handle_video(message, bot, file_id=file_id, filename=filename)
		# video note (circle)
		if message.video_note:
			file_id = message.video_note.file_id
			filename = f"videonote_{message.video_note.file_unique_id}.mp4"
			return await _handle_audio(message, bot, file_id=file_id, filename=filename)
		# documents that may contain audio or video
		if message.document:
			is_audio = _is_audio_document(message.document)
			is_video = _is_video_document(message.document)
			if is_audio or is_video:
				file_id = message.document.file_id
				filename = message.document.file_name or f"doc_{message.document.file_unique_id}"
				if is_video:
					return await _handle_video(message, bot, file_id=file_id, filename=filename)
				return await _handle_audio(message, bot, file_id=file_id, filename=filename)
			# Save non-audio/video documents to inbox
			file_id = message.document.file_id
			filename = message.document.file_name or f"doc_{message.document.file_unique_id}"
			await _save_file_to_inbox(bot, file_id, filename, message_type="document")
		
		# photo (save largest size)
		if message.photo:
			# Get largest photo size
			largest_photo = max(message.photo, key=lambda p: p.width * p.height)
			file_id = largest_photo.file_id
			# Determine extension from mime_type or use jpg as default
			ext = "jpg"
			if largest_photo.file_path:
				ext = largest_photo.file_path.rsplit(".", 1)[-1] if "." in largest_photo.file_path else "jpg"
			filename = f"photo_{largest_photo.file_unique_id}.{ext}"
			await _save_file_to_inbox(bot, file_id, filename, message_type="photo")
		
		# sticker
		if message.sticker:
			file_id = message.sticker.file_id
			# Determine extension from mime_type or use webp as default
			ext = "webp"
			if message.sticker.mime_type:
				ext = message.sticker.mime_type.split("/")[-1] if "/" in message.sticker.mime_type else "webp"
			filename = f"sticker_{message.sticker.file_unique_id}.{ext}"
			await _save_file_to_inbox(bot, file_id, filename, message_type="sticker")
		
		# animation (GIF)
		if message.animation:
			file_id = message.animation.file_id
			filename = message.animation.file_name or f"animation_{message.animation.file_unique_id}.gif"
			await _save_file_to_inbox(bot, file_id, filename, message_type="animation")
		
		# Handle non-audio/video messages
		if not any([message.voice, message.audio, message.video, message.video_note, 
		            message.document, message.photo, message.sticker, message.animation]):
			response_text = "Ожидается звуковой файл, видео или сообщение голосом"
			await message.answer(response_text)
			await _save_response(message, response_text, response_type="info")

	def _is_audio_document(doc: Document) -> bool:
		if doc.mime_type and doc.mime_type.startswith("audio/"):
			return True
		if doc.file_name:
			ext = doc.file_name.lower().rsplit(".", 1)[-1] if "." in doc.file_name else ""
			return ext in set(config.audio.formats)
		return False

	def _is_video_document(doc: Document) -> bool:
		"""Check if document is a video file."""
		if doc.mime_type and doc.mime_type.startswith("video/"):
			return True
		if doc.file_name:
			ext = doc.file_name.lower().rsplit(".", 1)[-1] if "." in doc.file_name else ""
			video_extensions = {"mp4", "avi", "mov", "mkv", "webm", "flv", "wmv", "m4v", "3gp"}
			return ext in video_extensions
		return False

	return router


