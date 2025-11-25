# План проекта (высокоуровневый)

См. детальный план в `tg.plan.md`. Ниже — краткое резюме этапов реализации.

Этапы:
1) Бутстрап: структура `src/`, `pyproject.toml`, `.env.example` (замена: `env.example`), docs.
2) Конфиг/логирование/хранилище (`src/core`).
3) Аудио‑пайплайн (`audio_io.py`, `chunking.py`), `ffmpeg`.
4) Провайдер `faster-whisper` (CUDA) + тестовый .bat.
5) Провайдер OpenAI + тестовый .bat.
6) Router провайдеров + fallback + тайм‑ауты + кэш.
7) Бот (`app.py`, `bot/router.py`) и UX.
8) Интеграционные тесты и бат‑скрипты запуска. [x] Unit-тесты для core/config, core/storage, transcription/router; скрипты run_tests.bat, run_coverage.bat. Manual tests (voce.mp3).
9) Документация (обновлена 2025-11-26: фиксы Windows/AMD, загрузка модели, инструкции, диагностика).
10) CI: Ruff и .gitignore.


