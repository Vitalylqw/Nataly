from __future__ import annotations

import json
import logging
from typing import Any, Awaitable, Callable

from aiogram import BaseMiddleware
from aiogram.types import Message, TelegramObject

from src.core.storage import Storage

logger = logging.getLogger(__name__)


class MessageLoggingMiddleware(BaseMiddleware):
	"""Middleware for automatic logging of incoming messages."""

	def __init__(self, storage: Storage) -> None:
		self.storage = storage

	async def __call__(
		self,
		handler: Callable[[TelegramObject, dict[str, Any]], Awaitable[Any]],
		event: TelegramObject,
		data: dict[str, Any],
	) -> Any:
		"""Process message before handler."""
		if not isinstance(event, Message):
			return await handler(event, data)

		try:
			message = event
			user_id = str(message.from_user.id) if message.from_user else "unknown"
			chat_id = str(message.chat.id) if message.chat else "unknown"
			message_id = message.message_id

			# Determine message type and extract content
			message_type = "other"
			content = None
			file_id = None
			file_unique_id = None
			filename = None
			mime_type = None

			if message.text:
				if message.text.startswith("/"):
					message_type = "command"
					content = message.text
				else:
					message_type = "text"
					content = message.text
			elif message.voice:
				message_type = "voice"
				file_id = message.voice.file_id
				file_unique_id = message.voice.file_unique_id
				filename = f"voice_{file_unique_id}.ogg"
				mime_type = "audio/ogg"
			elif message.audio:
				message_type = "audio"
				file_id = message.audio.file_id
				file_unique_id = message.audio.file_unique_id
				filename = message.audio.file_name
				mime_type = message.audio.mime_type
			elif message.video:
				message_type = "video"
				file_id = message.video.file_id
				file_unique_id = message.video.file_unique_id
				filename = message.video.file_name
				mime_type = message.video.mime_type
				content = message.caption
			elif message.video_note:
				message_type = "video_note"
				file_id = message.video_note.file_id
				file_unique_id = message.video_note.file_unique_id
				filename = f"videonote_{file_unique_id}.mp4"
				mime_type = "video/mp4"
			elif message.photo:
				message_type = "photo"
				# Get largest photo size
				largest_photo = max(message.photo, key=lambda p: p.width * p.height)
				file_id = largest_photo.file_id
				file_unique_id = largest_photo.file_unique_id
				ext = "jpg"
				if largest_photo.file_path:
					ext = largest_photo.file_path.rsplit(".", 1)[-1] if "." in largest_photo.file_path else "jpg"
				filename = f"photo_{file_unique_id}.{ext}"
				mime_type = "image/jpeg"
				content = message.caption
			elif message.sticker:
				message_type = "sticker"
				file_id = message.sticker.file_id
				file_unique_id = message.sticker.file_unique_id
				ext = "webp"
				if message.sticker.mime_type:
					ext = message.sticker.mime_type.split("/")[-1] if "/" in message.sticker.mime_type else "webp"
				filename = f"sticker_{file_unique_id}.{ext}"
				mime_type = message.sticker.mime_type or "image/webp"
			elif message.animation:
				message_type = "animation"
				file_id = message.animation.file_id
				file_unique_id = message.animation.file_unique_id
				filename = message.animation.file_name or f"animation_{file_unique_id}.gif"
				mime_type = message.animation.mime_type or "video/mp4"
				content = message.caption
			elif message.document:
				message_type = "document"
				file_id = message.document.file_id
				file_unique_id = message.document.file_unique_id
				filename = message.document.file_name
				mime_type = message.document.mime_type
				content = message.caption

			# Save message to database
			self.storage.save_message(
				message_id=message_id,
				user_id=user_id,
				chat_id=chat_id,
				message_type=message_type,
				content=content,
				file_id=file_id,
				file_unique_id=file_unique_id,
				filename=filename,
				mime_type=mime_type,
			)

			logger.debug(
				f"Saved message {message_id} from user {user_id}: "
				f"type={message_type}, content={content[:50] if content else None}"
			)

		except Exception as exc:
			logger.error(f"Error saving message to database: {exc}", exc_info=True)
			# Don't block message processing if logging fails

		return await handler(event, data)

