from __future__ import annotations

import logging
import sys
from pathlib import Path


def setup_logging(level: str = "INFO", log_file: str | None = None) -> None:
	"""Configure root logging with console and optional file output.
	
	Args:
		level: Logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)
		log_file: Optional path to log file. If provided, logs will be written to both
			console and file.
	"""
	root = logging.getLogger()
	if root.handlers:
		return

	log_level = getattr(logging, level.upper(), logging.INFO)
	root.setLevel(log_level)

	# Console handler with colored output-friendly format
	console_handler = logging.StreamHandler(sys.stdout)
	console_handler.setLevel(log_level)
	console_formatter = logging.Formatter(
		"%(asctime)s | %(levelname)-8s | %(name)s | %(message)s",
		datefmt="%Y-%m-%d %H:%M:%S",
	)
	console_handler.setFormatter(console_formatter)
	root.addHandler(console_handler)

	# File handler with detailed format (if log_file provided)
	if log_file:
		log_path = Path(log_file)
		log_path.parent.mkdir(parents=True, exist_ok=True)
		
		file_handler = logging.FileHandler(log_file, encoding="utf-8")
		file_handler.setLevel(log_level)
		file_formatter = logging.Formatter(
			"%(asctime)s | %(levelname)-8s | %(name)-30s | %(funcName)-20s | %(message)s",
			datefmt="%Y-%m-%d %H:%M:%S",
		)
		file_handler.setFormatter(file_formatter)
		root.addHandler(file_handler)

	# Suppress noisy third-party loggers
	logging.getLogger("httpx").setLevel(logging.WARNING)
	logging.getLogger("httpcore").setLevel(logging.WARNING)
	logging.getLogger("openai").setLevel(logging.WARNING)
	logging.getLogger("urllib3").setLevel(logging.WARNING)
	logging.getLogger("aiogram").setLevel(logging.INFO)


