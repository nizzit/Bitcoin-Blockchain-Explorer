# Bitcoin Blockchain Explorer

Минималистичный blockchain explorer для Bitcoin с современным веб-интерфейсом на основе HTMX.

> **⚠️ DISCLAIMER**  
> Данный проект создан при помощи AI-агента (Cline) с минимальным использованием ручного труда. Проект разработан в экспериментальных и образовательных целях для демонстрации возможностей автоматизированной разработки с использованием современных AI-инструментов. Рекомендуется тщательная проверка и тестирование кода перед использованием в production среде.

## 📋 Описание проекта

Bitcoin Blockchain Explorer - это веб-приложение для просмотра и анализа данных Bitcoin блокчейна. Проект предоставляет удобный интерфейс для изучения блоков, транзакций и адресов в сети Bitcoin.

### Основные возможности

- 🔍 **Поиск** - поиск блоков по хешу/высоте, транзакций по txid, адресов
- 📊 **Просмотр блоков** - детальная информация о блоках с пагинацией
- 💸 **Анализ транзакций** - просмотр входов, выходов и деталей транзакций
- 🏠 **Информация об адресах** - баланс, история транзакций и UTXO
- 🔄 **Автоматическая синхронизация** - фоновая синхронизация с Bitcoin Core
- ⚡ **Real-time обновления** - использование HTMX для динамического контента
- 📱 **Responsive дизайн** - адаптивный интерфейс для всех устройств

## 🏗️ Архитектура

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Browser   │◄──►│   FastAPI App   │◄──►│   Bitcoin Core  │
│   (HTMX UI)     │    │                 │    │   (RPC Server)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   SQLite DB     │
                       └─────────────────┘
```

## 🛠️ Технологический стек

### Backend
- **Python 3.12+** - основной язык программирования
- **FastAPI** - современный веб-фреймворк для создания API
- **SQLAlchemy** - ORM для работы с базой данных
- **Alembic** - система миграций базы данных
- **Pydantic** - валидация данных и схемы

### Frontend
- **HTML/CSS** - базовая структура и стили
- **HTMX** - динамические обновления без JavaScript
- **Jinja2** - шаблонизатор

### База данных
- **SQLite** - легковесная встраиваемая БД

### Bitcoin интеграция
- **python-bitcoinrpc** - клиент для взаимодействия с Bitcoin Core

### Управление зависимостями
- **uv** - быстрый менеджер пакетов Python

## 🚀 Установка и запуск

### 1. Клонирование репозитория

```bash
git clone <repository-url>
cd be2
```

### 2. Установка uv (если еще не установлен)

```bash
# Linux/macOS
curl -LsSf https://astral.sh/uv/install.sh | sh

# Windows
powershell -c "irm https://astral.sh/uv/install.ps1 | iex"
```

### 3. Установка зависимостей

```bash
uv sync
```

### 4. Настройка конфигурации

Создайте файл `.env` в корне проекта (или измените `app/config.py`):

```env
# Bitcoin RPC
BITCOIN_RPC_HOST=127.0.0.1
BITCOIN_RPC_PORT=8332
BITCOIN_RPC_USER=bitcoinrpc
BITCOIN_RPC_PASSWORD=your_secure_password

# Database
DATABASE_URL=sqlite:///./blockchain.db

# API
API_V1_STR=/api
PROJECT_NAME=Bitcoin Explorer

# Cache
CACHE_TTL=300
```

### 5. Инициализация базы данных

```bash
# Применение миграций
uv run alembic upgrade head
```

### 6. Запуск приложения

#### Development режим
```bash
uv run uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

#### Production режим
```bash
uv run uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4
```

Приложение будет доступно по адресу: http://localhost:8000

## 🔧 Использование

### Веб-интерфейс

После запуска откройте браузер и перейдите по адресу http://localhost:8000

- **Главная страница** (`/`) - последние блоки и транзакции
- **Блок** (`/block/{hash_or_height}`) - детальная информация о блоке
- **Транзакция** (`/tx/{txid}`) - информация о транзакции
- **Адрес** (`/address/{address}`) - информация об адресе

### API Endpoints

#### Блоки
- `GET /api/blocks` - Список последних блоков (с пагинацией)
- `GET /api/blocks/{hash_or_height}` - Информация о блоке
- `GET /api/blocks/latest` - Последний блок
- `GET /api/blocks/{hash}/transactions` - Транзакции блока

#### Транзакции
- `GET /api/transactions/{txid}` - Информация о транзакции
- `GET /api/transactions/latest` - Последние транзакции
- `GET /api/transactions/unconfirmed` - Неподтвержденные транзакции

#### Адреса
- `GET /api/addresses/{address}` - Информация об адресе
- `GET /api/addresses/{address}/transactions` - Транзакции адреса
- `GET /api/addresses/{address}/utxos` - UTXO адреса

#### Поиск
- `GET /api/search?q={query}` - Универсальный поиск

#### Синхронизация
- `GET /api/sync/status` - Статус синхронизации
- `POST /api/sync/start` - Запуск синхронизации последних блоков
- `POST /api/sync/full` - Запуск полной синхронизации
- `POST /api/sync/mempool` - Синхронизация мемпула
- `GET /api/sync/stats` - Статистика синхронизации

### Примеры API запросов

```bash
# Получить последние блоки
curl http://localhost:8000/api/blocks?limit=10

# Получить блок по хешу
curl http://localhost:8000/api/blocks/00000000839a8e6886ab5951d76f411475428afc90947ee320161bbf18eb6048

# Получить блок по высоте
curl http://localhost:8000/api/blocks/1

# Получить транзакцию
curl http://localhost:8000/api/transactions/0e3e2357e806b6cdb1f70b54c3a3a17b6714ee1f0e68bebb44a74b1efd512098

# Поиск
curl http://localhost:8000/api/search?q=1A1zP1eP5QGefi2DMPTfTL5SLmv7DivfNa

# Запуск синхронизации
curl -X POST http://localhost:8000/api/sync/start?max_blocks=100

# Проверка статуса
curl http://localhost:8000/api/sync/status
```

## 🐳 Docker (опционально)

### Сборка образа
```bash
docker build -t bitcoin-explorer .
```

### Запуск контейнера
```bash
docker run -d \
  -p 8000:8000 \
  -e BITCOIN_RPC_HOST=host.docker.internal \
  -e BITCOIN_RPC_USER=bitcoinrpc \
  -e BITCOIN_RPC_PASSWORD=your_secure_password \
  -v $(pwd)/blockchain.db:/app/blockchain.db \
  bitcoin-explorer
```

### Docker Compose
```bash
docker-compose up -d
```

## 📝 Структура проекта

```
be2/
├── app/                       # Основное приложение
│   ├── main.py                # FastAPI приложение
│   ├── config.py              # Конфигурация
│   ├── database.py            # Настройка БД
│   ├── api/                   # API endpoints
│   │   ├── blocks.py          # Endpoints для блоков
│   │   ├── transactions.py    # Endpoints для транзакций
│   │   ├── addresses.py       # Endpoints для адресов
│   │   ├── search.py          # Поиск
│   │   └── sync.py            # Синхронизация
│   ├── models/                # SQLAlchemy модели
│   │   ├── block.py
│   │   ├── transaction.py
│   │   └── address.py
│   ├── schemas/               # Pydantic схемы
│   ├── services/              # Бизнес-логика
│   │   ├── bitcoin_rpc.py     # Bitcoin RPC клиент
│   │   ├── block_service.py
│   │   ├── transaction_service.py
│   │   └── sync_service.py    # Синхронизация
│   ├── templates/             # HTML шаблоны
│   └── static/                # CSS/JS файлы
├── migrations/                # Alembic миграции
├── pyproject.toml             # Конфигурация проекта
└── README.md                  # Этот файл
```

## 🔄 Синхронизация с блокчейном

### Автоматическая синхронизация

Приложение автоматически запускает фоновую задачу синхронизации при старте. Синхронизация выполняется каждые 30 секунд.

### Ручная синхронизация

```bash
# Синхронизировать последние 100 блоков
curl -X POST http://localhost:8000/api/sync/start?max_blocks=100

# Полная синхронизация всего блокчейна (может занять много времени!)
curl -X POST http://localhost:8000/api/sync/full?batch_size=100

# Синхронизация мемпула
curl -X POST http://localhost:8000/api/sync/mempool
```

### Мониторинг синхронизации

```bash
# Статус синхронизации
curl http://localhost:8000/api/sync/status

# Статистика
curl http://localhost:8000/api/sync/stats
```

## 📚 Документация API

После запуска приложения автоматически генерируется интерактивная документация API:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc
