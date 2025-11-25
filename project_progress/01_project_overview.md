# Описание и цель проекта

Цель: локальный Telegram‑бот (Windows 10, long polling), который принимает голос/аудио
разных форматов, автоматически определяет язык и возвращает транскрипт текста.

Архитектура: монолит. Основной провайдер — локальный faster‑whisper (GPU), резерв — OpenAI.

Ключевые требования:
- Мультиязычность, авто‑детект языка
- Поддержка voice/audio/video_note/документов (ogg/opus, mp3, m4a, wav, webm, flac)
- Конверсия в WAV 16kHz mono (ffmpeg)
- Кэш транскриптов по хэшу
- Документация прогресса в `project_progress/*`

Релевантные решения:
- `aiogram 3` для бота
- `faster-whisper` (CUDA, float16) + OpenAI API как резерв
- **Стабильность на Windows**: `numpy==1.26.4` + `ctranslate2==4.0.0` (фикс вылетов на AMD)
- **Модель**: Строгая загрузка из `var/models/faster-whisper-large-v3` (`local_files_only=True`)
- Конфиг через `.env` + `src/config/settings.yaml`
- Хранилище: SQLite + файлы в `var/`
- Тестирование: `pytest` + `pytest-cov` (покрытие 57%), unit-тесты для core/config, core/storage, transcription/router

## Подключение провайдеров (кратко)
- Локально: `pip install faster-whisper` и установите `ffmpeg`. 
  **Важно:** запустите `scripts\servises\download_faster_whisper_model.bat` для загрузки модели в `var/models`.
  Путь к ffmpeg можно указать в `paths.ffmpeg_bin` (`src/config/settings.yaml`). 
  Модель по умолчанию: `large-v3` (CUDA, ~3GB VRAM при int8/float16).
- Облако (резерв): `pip install openai`, задайте `OPENAI_API_KEY` в `.env`.
  Модель: `gpt-4o-mini-transcribe` (fallback: `whisper-1`).


