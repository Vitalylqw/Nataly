import logging

from aiogram import Bot, Dispatcher
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand

from src.bot.router import get_router
from src.core.config import load_config
from src.core.logging import setup_logging
from src.core.storage import Storage

logger = logging.getLogger(__name__)


async def main() -> None:
	"""Entrypoint for polling run."""
	config = load_config()
	
	# Setup logging with file output in production
	log_file = None
	if config.env == "prod":
		log_file = "var/app.log"
	
	log_level = "DEBUG" if config.env == "dev" else "INFO"
	setup_logging(level=log_level, log_file=log_file)
	
	logger.info(f"Starting Telegram Audio Transcriber (env: {config.env})")
	logger.info(f"Provider: {config.provider.default}, Fallback: {config.provider.fallback}")

	bot = Bot(
		token=config.telegram_token,
		default=DefaultBotProperties(parse_mode=ParseMode.HTML)
	)
	dp = Dispatcher(storage=MemoryStorage())
	dp.include_router(get_router(config=config))

	# Ensure storage and runtime dirs
	storage = Storage(config)
	storage.ensure_runtime_dirs()
	storage.init_db()
	logger.info("Storage initialized")

	# Minimal bot commands
	await bot.set_my_commands(
		[
			BotCommand(command="start", description="Начать"),
			BotCommand(command="help", description="Помощь"),
			BotCommand(command="settings", description="Настройки"),
		]
	)
	logger.info("Bot commands registered")
	logger.info("Starting polling...")
	await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())


if __name__ == "__main__":
	# Lazy import to run async main with Python 3.10+
	import asyncio

	asyncio.run(main())


