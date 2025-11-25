# Telegram Audio Transcriber (Windows 10, monolith)

Telegram‑бот для транскрибации аудио/voice. Основной провайдер — локальный `faster-whisper`
(GPU CUDA), резерв — OpenAI (Whisper API / gpt‑4o‑mini‑transcribe).

## Установка и требования (Windows 10)

### Основные требования
- Python 3.10+
- Git
- FFmpeg (должен быть в PATH или прописан в `settings.yaml`)
- **Важно для Windows (AMD CPU):** Используются фиксированные версии `numpy==1.26.4` и `ctranslate2==4.0.0` во избежание конфликтов (Access Violation).

### Быстрый старт

1) Клонируйте репозиторий и создайте виртуальное окружение:
```
python -m venv venv
```

2) Активируйте окружение:
```
venv\Scripts\activate.bat
```

3) Установите зависимости:
```
pip install -e .
```

4) Создайте `.env` (см. `env.example`) и настройте ключи (Telegram, OpenAI).

5) **Скачайте модель** (обязательно для локальной работы):
```
scripts\servises\download_faster_whisper_model.bat
```
Модель `faster-whisper-large-v3` будет сохранена в `var/models/` и загружаться строго локально.

6) Запустите бота:
```
scripts\servises\run_bot.bat
```

## Структура и скрипты
См. `project_progress/02_plan.md` и `src/`.

Полезные скрипты в `scripts/`:
- `servises/download_faster_whisper_model.bat` — загрузка модели.
- `servises/download_ffmpeg.bat` — загрузка FFmpeg.
- `test/test_voce_simple.py` — ручной тест транскрибации (требует `voce.mp3`).

## Тестирование

Запуск тестов:
```bash
scripts\test\run_tests.bat
```

Проверка покрытия кода:
```bash
scripts\test\run_coverage.bat
```

Текущее покрытие: 57% (8 passed, 1 skipped). Unit-тесты покрывают: `core/config`, `core/storage`, `transcription/router`.

## Качество кода
- Линтер: Ruff (`pyproject.toml`)
- Стиль: PEP8, длина строки 100
- Тесты: pytest + pytest-cov
- Логирование: структурированное логирование с поддержкой файлов (prod) и консоли (dev)

## Примечания
- Работает без вебхуков (long polling).
- Локальный провайдер использует GPU (если доступна CUDA), при ошибках — fallback в облако.
- Временные файлы в `var/` (в .gitignore).
- Логи в продакшне пишутся в `var/app.log`, в dev режиме — только в консоль.
- Уровень логирования: DEBUG (dev), INFO (prod).


