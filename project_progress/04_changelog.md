# Хронологический журнал

- init: создан каркас проекта, pyproject.toml, базовые документы и .gitignore.
- core: добавлены config/logging/storage (SQLite), settings.yaml.
- audio: добавлены конвертация в WAV 16k/mono (ffmpeg) и чанкинг.
- providers: реализованы faster-whisper (CUDA) и OpenAI, тестовые .bat.
- router: выбор провайдера, тайм-ауты, fallback, кэш в SQLite.
- bot: обработчики /start /help /settings и приём аудио/voice/video_note/документов.
- tests: unit и smoke, бат-скрипт запуска pytest.


2025-11-21
- **Dependencies**: Обновлен `requirements.txt`. Зафиксированы `numpy==1.26.4` и `ctranslate2==4.0.0` для исправления "Access Violation" на Windows (AMD CPU). Добавлен `requests>=2.31.0` (отсутствующая зависимость для `faster-whisper` 1.0.3).
- **Providers**: `src/transcription/providers/faster_whisper.py` переработан для строгой загрузки локальной модели из `var/models/faster-whisper-large-v3`. Добавлен флаг `local_files_only=True` для запрета обращений к Hugging Face.
- scripts/test/run_tests.bat: сделан независимым от текущей директории с использованием `%~dp0`, переходом в корень проекта и явным вызовом `venv\Scripts\python.exe -m pytest -q`. Корректный код выхода передается наружу.
- Результат после фикса: тесты проходят (2 passed, 1 skipped).
- scripts/servises/download_faster_whisper_model.py: добавлен утилитный скрипт для скачивания модели faster‑whisper через инициализацию `WhisperModel` (CPU по умолчанию). Поддерживает `--model`, `--device`, `--compute-type`. 
- scripts/servises/download_faster_whisper_model.bat: бат‑обёртка с проверкой venv и прокидыванием аргументов.
- pyproject: добавлен `pytest-cov` в dev-зависимости; создан `scripts/test/run_coverage.bat`, который зеркалит `run_tests.bat`, но запускает `pytest --cov=src --cov-report=term-missing`.
- tests: добавлены `tests/test_core_config.py`, `tests/test_core_storage.py`, `tests/test_transcription_router_unit.py`. Покрыто: загрузка конфигурации (.env + settings + директории), upsert в SQLite-хранилище (transcripts/user_settings), логика `TranscriptionRouter` (кэш-хит, fallback на облако, склейка чанков и смещения сегментов) без тяжелых зависимостей (ffmpeg/faster-whisper).
- Результат `scripts/test/run_coverage.bat`: 8 passed, 1 skipped, покрытие 59%. Heavy smoke по-прежнему `skip` при отсутствии faster-whisper/ffmpeg.
- Ruff прогнан для новых тестов; всплыло предупреждение о переходе на `[tool.ruff.lint]` (TODO для обновления конфигурации).
- Smoke-тест faster-whisper/ffmpeg:
  - Команда: `venv\Scripts\python.exe -m pytest tests\test_transcription_router_smoke.py -vv -rs`
  - Результат: `SKIPPED (Model may not be available locally; skip heavy smoke test)`
  - Что дальше: предзагрузить модель faster-whisper и убедиться в наличии `ffmpeg`
- **Tests**: Выполнен ручной тест `scripts/test/test_voce_simple.py` на файле `voce.mp3`. Подтверждена работоспособность пайплайна транскрибации с локальной моделью (Provider: local:faster-whisper).

2025-11-26
- **Bot Runtime Fix**: Обновлен `src/app.py` для совместимости с `aiogram 3.22.0`. Использован `DefaultBotProperties` вместо устаревшего параметра `parse_mode` в конструкторе `Bot`.
- **Diagnostic Suite**: Добавлен набор скриптов для глубокой диагностики и обслуживания окружения (Windows/CUDA):
  - `scripts/servises/`: `test_cuda.py`, `recreate_venv.bat`, `copy_model_to_project.py`.
  - `scripts/test/`: `benchmark_cuda.py` (замер скорости транскрибации), `check_cuda.py`, `check_db.py`, `debug_env.py`.
  - `scripts/debug/`: `check_model_cache.py`, `test_faster_whisper_simple.py`.
- **Dependencies**: Обновлен `requirements.txt` для соответствия текущему окружению (aiogram 3.22.0, pydantic 2.x).
- **Status**: Приложение запущено в режиме Polling, транскрибация работает на GPU (при наличии CUDA) и CPU.
- **Project Structure**: Финализация структуры скриптов (debug, servises), обновление .gitignore (исключение артефактов тестов, venv), удаление устаревшего скрипта покрытия.
