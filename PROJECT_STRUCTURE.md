# TeleDAV - Структура проекта и описание файлов

## 📁 Полная структура проекта

```
TeleDAV/
├── teledav/
│   ├── __init__.py
│   ├── main.py                    # Точка входа приложения
│   ├── config.py                  # Конфигурация из .env
│   │
│   ├── db/
│   │   ├── __init__.py
│   │   ├── models.py              # ORM модели (Folder, File, FileChunk)
│   │   ├── service.py             # DatabaseService с CRUD операциями
│   │   └── __pycache__/
│   │
│   ├── bot/
│   │   ├── __init__.py
│   │   ├── service.py             # TelegramService для работы с ботом
│   │   ├── handlers.py            # Обработчики команд (опционально)
│   │   └── __pycache__/
│   │
│   ├── webdav/
│   │   ├── __init__.py
│   │   ├── app.py                 # FastAPI приложение
│   │   ├── provider.py            # WebDAV провайдер
│   │   ├── provider_new.py        # Резервная копия провайдера
│   │   └── __pycache__/
│   │
│   ├── utils/
│   │   ├── __init__.py
│   │   ├── chunking.py            # Утилиты для разделения файлов
│   │   └── __pycache__/
│   │
│   └── __pycache__/
│
├── tests/
│   └── __init__.py
│
├── docker-compose.yml             # Docker Compose конфигурация
├── Dockerfile                     # Docker image конфигурация
├── requirements.txt               # Python зависимости
│
├── .env.example                   # Пример конфигурации
├── .env                           # Реальная конфигурация (локально)
│
├── README.md                      # Основная документация (новая)
├── README_FULL.md                 # Полная документация с примерами
├── IMPLEMENTATION.md              # Этот файл - описание реализации
│
└── teledav.db                     # SQLite база данных (генерируется)
```

## 📄 Описание основных файлов

### 🎯 teledav/main.py
**Назначение:** Главная точка входа приложения

**Основные функции:**
- `main()` - инициализация и запуск сервера
- Настройка логирования
- Создание таблиц БД
- Запуск uvicorn сервера

**Особенности:**
- Красивый вывод при запуске
- Обработка Ctrl+C
- Информативные сообщения об ошибках

### 🔧 teledav/config.py
**Назначение:** Загрузка и валидация конфигурации из .env

**Параметры:**
```python
class Settings:
    bot_token: str              # Токен Telegram бота
    chat_id: int               # ID группы
    dav_username: str          # Пользователь WebDAV
    dav_password: str          # Пароль WebDAV
    dav_host: str              # Адрес слушания
    dav_port: int              # Порт
    database_url: str          # URL базы данных
    chunk_size: int            # Размер части файла
```

### 🗄️ teledav/db/models.py
**Назначение:** ORM модели для работы с БД

**Модели:**

1. **Folder**
   - Представляет папку/тему в WebDAV
   - Связана с Telegram Topic
   - Содержит файлы

2. **File**
   - Представляет загруженный файл
   - Разбита на части (chunks)
   - Хранит метаданные

3. **FileChunk**
   - Часть файла (для больших файлов)
   - Связана с сообщением в Telegram
   - Хранит порядок сборки

**Отношения:**
```
Folder (1) ──────── (N) File
File (1) ──────---- (N) FileChunk
```

### 💾 teledav/db/service.py
**Назначение:** Сервис для работы с базой данных

**DatabaseService - методы:**

**Папки (Folders):**
- `create_folder(name, path)` → Folder
- `get_folder_by_path(path)` → Folder | None
- `get_folder_by_id(folder_id)` → Folder | None
- `get_all_folders()` → List[Folder]
- `update_folder_topic(folder_id, topic_id)` → Folder | None
- `delete_folder(folder_id)` → bool

**Файлы (Files):**
- `create_file(folder_id, name, path, size, mime_type)` → File
- `get_file_by_path(path)` → File | None
- `get_file_by_id(file_id)` → File | None
- `get_files_by_folder(folder_id)` → List[File]
- `delete_file(file_id)` → bool

**Части файлов (FileChunks):**
- `create_chunk(file_id, chunk_number, size)` → FileChunk
- `update_chunk_message_ids(chunk_id, message_id, thread_id)` → FileChunk | None
- `get_chunks_by_file(file_id)` → List[FileChunk]
- `get_chunk_by_id(chunk_id)` → FileChunk | None
- `delete_chunks_by_file(file_id)` → bool

**Использование:**
```python
async with AsyncSessionLocal() as session:
    db = DatabaseService(session)
    folder = await db.create_folder("Documents", "/Documents")
    file = await db.create_file(folder.id, "doc.pdf", "/Documents/doc.pdf", 1000000)
```

### ✂️ teledav/utils/chunking.py
**Назначение:** Утилиты для разделения и сборки файлов

**Constants:**
- `CHUNK_SIZE = 49.9 * 1024 * 1024` # 49.9 МБ (максимум Telegram)

**Функции:**

1. `calculate_chunks(file_size)` → int
   - Рассчитывает количество частей
   - Пример: 100 MB → 3 части

2. `read_chunks(fp, chunk_size)` → AsyncGenerator[bytes]
   - Читает файл по частям
   - Асинхронная работа

3. `read_chunks_from_stream(file_stream, file_size)` → AsyncGenerator[Tuple[int, bytes]]
   - Разделяет BytesIO на части
   - Возвращает (номер_части, данные)

4. `get_chunk_info(file_size)` → dict
   - Полная информация о разделении
   - Включает offset каждой части

**Пример:**
```python
# 100 MB файл → 3 части по 49.9, 49.9, 0.2 МБ
chunk_info = get_chunk_info(100 * 1024 * 1024)
# {
#   'total_chunks': 3,
#   'file_size': 104857600,
#   'chunks': [
#     {'number': 0, 'size': 52298240, 'offset': 0},
#     {'number': 1, 'size': 52298240, 'offset': 52298240},
#     {'number': 2, 'size': 261120, 'offset': 104596480}
#   ]
# }
```

### 🤖 teledav/bot/service.py
**Назначение:** Сервис для взаимодействия с Telegram ботом

**TelegramService - методы:**

**Управление темами:**
- `create_topic(name)` → int | None
  - Создает новую тему в группе
  - Возвращает ID темы

- `delete_topic(topic_id)` → bool
  - Удаляет тему со всеми сообщениями

**Загрузка:**
- `upload_chunk(topic_id, data, file_name, chunk_number)` → tuple | None
  - Загружает одну часть
  - Возвращает (message_id, file_id)

- `upload_chunks_parallel(topic_id, chunks, file_name)` → List[tuple]
  - Загружает все части одновременно (asyncio.gather)
  - Гораздо быстрее!

**Удаление:**
- `delete_files(message_ids)` → bool
  - Удаляет несколько сообщений параллельно

**Скачивание:**
- `download_chunk(file_id)` → bytes | None
  - Загружает данные части из Telegram

**Пример использования:**
```python
# Создаем тему и загружаем файл
topic_id = await telegram_service.create_topic("My Documents")
chunks = [chunk1_data, chunk2_data, chunk3_data]
results = await telegram_service.upload_chunks_parallel(
    topic_id, chunks, "document.pdf"
)
# results = [(12345, 'file_id_1'), (12346, 'file_id_2'), (12347, 'file_id_3')]
```

### 🌐 teledav/webdav/provider.py
**Назначение:** WebDAV провайдер для wsgidav

**TeleDAVResource (файл):**
- `get_content_length()` → int
- `get_content_type()` → str
- `get_display_name()` → str
- `get_last_modified()` → float
- `get_content()` → bytes (асинхронно)
- `put_content()` → None (загрузка)
- `delete()` → None (удаление)

**TeleDAVCollection (папка):**
- `get_display_name()` → str
- `get_member_list()` → List
- `mkcol(name)` → TeleDAVCollection (создание папки)

**TeleDAVProvider (главный провайдер):**
- Наследует DAVProvider из wsgidav
- `get_resource_inst()` - получить ресурс по пути
- `delete()` - удалить файл или папку

**Логика загрузки файла:**
1. Клиент отправляет PUT запрос
2. `put_content()` вызывается
3. Файл буферизуется в памяти
4. Рассчитываются части
5. Каждая часть сохраняется в БД
6. Все части загружаются параллельно в Telegram
7. Message IDs сохраняются в БД

### 🚀 teledav/webdav/app.py
**Назначение:** FastAPI приложение с WebDAV

**Компоненты:**

1. **SimpleDomainControllerImpl** - аутентификация
   - Basic Auth реализация
   - Проверка username/password

2. **dav_config** - конфигурация WsgiDAV
   - Provider mapping
   - Аутентификация
   - CORS
   - Логирование

3. **app** - FastAPI приложение
   - CORS middleware
   - WsgiDAVApp mounted
   - Lifecycle events

**Events:**
- `@startup` - инициализация БД
- `@shutdown` - очистка

## 🔑 Ключевые концепции

### Асинхронность
```python
# Все операции с БД и Telegram асинхронные
async with AsyncSessionLocal() as session:
    db = DatabaseService(session)
    file = await db.create_file(...)
```

### Параллелизм
```python
# Несколько задач одновременно
results = await asyncio.gather(
    telegram_service.upload_chunk(data1),
    telegram_service.upload_chunk(data2),
    telegram_service.upload_chunk(data3)
)
```

### Потоковость
```python
# Файлы обрабатываются в памяти (BytesIO)
buffer = io.BytesIO()
buffer.write(chunk)
buffer.seek(0)
```

## 🔄 Типичные процессы

### Процесс 1: Создание папки
```
Клиент → WebDAV MKCOL /Documents
  ↓
TeleDAVProvider.mkcol()
  ↓
DatabaseService.create_folder()  # Сохраняем в БД
  ↓
TelegramService.create_topic()   # Создаем тему
  ↓
DatabaseService.update_folder_topic()  # Сохраняем ID
  ↓
✓ Папка создана
```

### Процесс 2: Загрузка файла
```
Клиент → WebDAV PUT /Documents/file.pdf (100 MB)
  ↓
TeleDAVProvider.put_content()
  ↓
Буферизуем данные → BytesIO
  ↓
calculate_chunks(100 MB) → 3 части
  ↓
Параллельно загружаем в Telegram:
  ├─ upload_chunk(chunk1) → message_id: 12345
  ├─ upload_chunk(chunk2) → message_id: 12346
  └─ upload_chunk(chunk3) → message_id: 12347
  ↓
Сохраняем в БД:
  ├─ FileChunk(message_id=12345, chunk_number=0)
  ├─ FileChunk(message_id=12346, chunk_number=1)
  └─ FileChunk(message_id=12347, chunk_number=2)
  ↓
✓ Файл загружен
```

### Процесс 3: Скачивание файла
```
Клиент → WebDAV GET /Documents/file.pdf
  ↓
TeleDAVProvider.get_content()
  ↓
DatabaseService.get_chunks_by_file()
  ↓
Параллельно скачиваем из Telegram:
  ├─ download_chunk(message_id=12345) → chunk1
  ├─ download_chunk(message_id=12346) → chunk2
  └─ download_chunk(message_id=12347) → chunk3
  ↓
Объединяем части в порядке chunk_number
  ↓
Отправляем клиенту
  ↓
✓ Файл скачан
```

### Процесс 4: Удаление файла
```
Клиент → WebDAV DELETE /Documents/file.pdf
  ↓
TeleDAVProvider.delete()
  ↓
DatabaseService.get_chunks_by_file()
  ↓
TelegramService.delete_files([12345, 12346, 12347])
  ↓
DatabaseService.delete_file()
  ↓
✓ Файл удален (все части удалены из Telegram)
```

## 📦 Зависимости и их роль

| Пакет | Версия | Роль |
|-------|--------|------|
| aiogram | 3.4.1 | Telegram Bot API клиент |
| fastapi | 0.110.0 | Веб-фреймворк |
| uvicorn | 0.27.1 | ASGI сервер |
| SQLAlchemy | 2.0.25 | ORM для БД |
| wsgidav | 4.2.0 | WebDAV сервер |
| aiosqlite | 0.19.0 | Асинхронный драйвер SQLite |
| python-dotenv | 1.0.1 | Загрузка .env файлов |
| pydantic | 2.5.3 | Валидация данных |

## 🔒 Безопасность

- **Basic Auth** - встроена в WsgiDAV через SimpleDomainController
- **Token** - Telegram Bot Token в .env (не коммитим)
- **Приватная группа** - только бот может загружать файлы
- **Изоляция по темам** - каждая папка имеет свою тему

## 🎯 Что можно расширить

1. **Digest Auth** вместо Basic
2. **S3** вместо Telegram
3. **Encryption** файлов
4. **Compression** перед загрузкой
5. **Sync** с облачными сервисами
6. **API** для программного доступа
7. **Web UI** для управления

---

**Проект готов к деплою и использованию!** 🚀
