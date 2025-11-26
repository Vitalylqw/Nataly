# План реализации: Сохранение всех сообщений и действий с ботом

## Цель
Реализовать полное логирование всех взаимодействий пользователей с ботом: входящие сообщения, исходящие ответы, команды, действия и ошибки.

## Анализ текущего состояния

### Что уже сохраняется:
- Транскрипты аудио (таблица `transcripts`) - по хэшу файла
- Настройки пользователей (таблица `user_settings`)

### Что нужно добавить:
- Все входящие сообщения (команды, текстовые, аудио, документы)
- Все исходящие ответы бота
- Метаданные взаимодействий (user_id, chat_id, timestamp, message_id)
- События и действия (команды, ошибки, статусы обработки)

## Проектирование схемы БД

### Таблица `messages` (входящие сообщения)
```sql
CREATE TABLE messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER NOT NULL,
    user_id TEXT NOT NULL,
    chat_id TEXT NOT NULL,
    message_type TEXT NOT NULL,  -- 'command', 'text', 'voice', 'audio', 'video_note', 'document', 'other'
    content TEXT,  -- текст сообщения или команда
    file_id TEXT,  -- для медиа-файлов
    file_unique_id TEXT,
    filename TEXT,
    mime_type TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE(message_id, chat_id)
)
```

### Таблица `bot_responses` (исходящие ответы)
```sql
CREATE TABLE bot_responses (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER,  -- ID исходного сообщения (FK к messages)
    user_id TEXT NOT NULL,
    chat_id TEXT NOT NULL,
    response_type TEXT NOT NULL,  -- 'text', 'error', 'processing'
    content TEXT NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### Таблица `events` (события и действия)
```sql
CREATE TABLE events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    message_id INTEGER,  -- опционально, если связано с сообщением
    user_id TEXT NOT NULL,
    event_type TEXT NOT NULL,  -- 'command_start', 'command_help', 'transcription_start', 'transcription_success', 'transcription_error', 'error'
    details TEXT,  -- JSON с дополнительными данными
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
)
```

### Обновление таблицы `transcripts`
Добавить связь с сообщениями:
```sql
ALTER TABLE transcripts ADD COLUMN message_id INTEGER;
ALTER TABLE transcripts ADD COLUMN user_id TEXT;
```

## Архитектура решения

### 1. Middleware для перехвата сообщений
Создать middleware в aiogram для автоматического сохранения всех входящих сообщений перед обработкой.

### 2. Расширение Storage класса
Добавить методы:
- `save_message()` - сохранение входящего сообщения
- `save_bot_response()` - сохранение ответа бота
- `save_event()` - сохранение события/действия
- `get_user_messages()` - получение истории сообщений пользователя
- `get_message_by_id()` - получение сообщения по ID

### 3. Интеграция в существующие обработчики
- Обновить `bot/router.py` для сохранения сообщений и ответов
- Добавить сохранение событий в ключевых точках (команды, транскрипция, ошибки)

### 4. Обработка ошибок
Сохранять все исключения в таблицу `events` с типом `error`.

## Этапы реализации

### Этап 1: Расширение схемы БД
1. Обновить `Storage.init_db()` для создания новых таблиц
2. Добавить миграцию для существующих данных (если нужно)
3. Обновить `transcripts` таблицу

### Этап 2: Расширение Storage класса
1. Добавить методы сохранения сообщений, ответов и событий
2. Добавить методы получения данных
3. Протестировать методы

### Этап 3: Создание Middleware
1. Создать middleware для перехвата входящих сообщений
2. Интегрировать в `app.py`
3. Протестировать автоматическое сохранение

### Этап 4: Интеграция в обработчики
1. Обновить `bot/router.py` для сохранения ответов
2. Добавить сохранение событий в командах
3. Добавить сохранение событий транскрипции
4. Добавить обработку ошибок

### Этап 5: Тестирование
1. Unit-тесты для Storage методов
2. Интеграционные тесты для middleware
3. Проверка сохранения всех типов сообщений
4. Проверка производительности

## Детали реализации

### Типы сообщений (message_type):
- `command` - команды (/start, /help, /settings)
- `text` - текстовые сообщения
- `voice` - голосовые сообщения
- `audio` - аудиофайлы
- `video_note` - видеосообщения
- `document` - документы (аудио)
- `other` - прочие типы

### Типы ответов (response_type):
- `text` - текстовый ответ
- `error` - сообщение об ошибке
- `processing` - сообщение о процессе обработки

### Типы событий (event_type):
- `command_start` - команда /start
- `command_help` - команда /help
- `command_settings` - команда /settings
- `transcription_start` - начало транскрипции
- `transcription_success` - успешная транскрипция
- `transcription_error` - ошибка транскрипции
- `error` - общая ошибка

## Производительность и оптимизация

1. Использовать индексы для частых запросов:
   - `CREATE INDEX idx_messages_user_id ON messages(user_id)`
   - `CREATE INDEX idx_messages_created_at ON messages(created_at)`
   - `CREATE INDEX idx_events_user_id ON events(user_id)`

2. Асинхронное сохранение (опционально):
   - Использовать очередь задач для сохранения
   - Не блокировать обработку сообщений

3. Очистка старых данных (опционально):
   - Настройка хранения данных (например, последние N дней)
   - Периодическая очистка

## Риски и ограничения

1. Рост размера БД - нужно предусмотреть очистку или архивацию
2. Производительность - индексы и оптимизация запросов
3. Конфиденциальность - данные пользователей хранятся локально

## Дополнительные возможности (будущее)

1. Экспорт истории в JSON/CSV
2. Статистика использования бота
3. Поиск по истории сообщений
4. API для доступа к истории

