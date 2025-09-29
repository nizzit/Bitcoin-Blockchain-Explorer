# План разработки Bitcoin Blockchain Explorer

## 1. Обзор проекта

**Цель**: Создание минималистичного blockchain explorer'а для Bitcoin с современным веб-интерфейсом.

**Технологический стек**:
- Backend: Python 3.12+ + FastAPI
- База данных: SQLite
- Frontend: HTML + CSS + HTMX
- Bitcoin интеграция: Bitcoin RPC клиент
- Управление проектом и зависимостями: uv

## 2. Архитектура системы

```
┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐
│   Web Browser   │◄──►│   FastAPI App   │◄──►│   Bitcoin Core  │
│   (HTMX UI)     │    │                 │    │   (RPC Server)  │
└─────────────────┘    └─────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌─────────────────┐
                       │   SQLite DB     │
                       │                 │
                       └─────────────────┘
```

### Основные компоненты:

1. **API Layer** - FastAPI endpoints для получения данных
2. **Service Layer** - бизнес-логика и обработка данных
3. **Data Layer** - модели SQLAlchemy и работа с БД
4. **Bitcoin Integration** - RPC клиент для взаимодействия с Bitcoin Core
5. **Web Interface** - HTMX-powered фронтенд
6. **Background Tasks** - синхронизация с блокчейном

## 3. Структура проекта

```
be2/
├── app/
│   ├── __init__.py
│   ├── main.py                 # FastAPI приложение
│   ├── config.py              # Конфигурация
│   ├── database.py            # Настройка БД
│   ├── models/
│   │   ├── __init__.py
│   │   ├── block.py           # Модель блока
│   │   ├── transaction.py     # Модель транзакции
│   │   └── address.py         # Модель адреса
│   ├── schemas/
│   │   ├── __init__.py
│   │   ├── block.py           # Pydantic схемы для блоков
│   │   ├── transaction.py     # Pydantic схемы для транзакций
│   │   └── address.py         # Pydantic схемы для адресов
│   ├── services/
│   │   ├── __init__.py
│   │   ├── bitcoin_rpc.py     # Bitcoin RPC клиент
│   │   ├── block_service.py   # Сервис для работы с блоками
│   │   ├── transaction_service.py # Сервис для транзакций
│   │   └── sync_service.py    # Синхронизация с блокчейном
│   ├── api/
│   │   ├── __init__.py
│   │   ├── blocks.py          # API endpoints для блоков
│   │   ├── transactions.py    # API endpoints для транзакций
│   │   ├── addresses.py       # API endpoints для адресов
│   │   └── search.py          # API endpoints для поиска
│   ├── templates/
│   │   ├── base.html          # Базовый шаблон
│   │   ├── index.html         # Главная страница
│   │   ├── block.html         # Страница блока
│   │   ├── transaction.html   # Страница транзакции
│   │   ├── address.html       # Страница адреса
│   │   └── components/        # HTMX компоненты
│   │       ├── block_list.html
│   │       ├── tx_list.html
│   │       └── search_results.html
│   └── static/
│       ├── css/
│       │   └── style.css      # Стили
│       └── js/
│           └── app.js         # Минимальный JS (если нужен)
├── migrations/                 # Alembic миграции
├── tests/                     # Тесты
├── requirements.txt
├── pyproject.toml
├── README.md
└── plan.md
```

## 4. Схема базы данных

### Таблица `blocks`
```sql
CREATE TABLE blocks (
    id INTEGER PRIMARY KEY,
    hash VARCHAR(64) UNIQUE NOT NULL,
    height INTEGER UNIQUE NOT NULL,
    version INTEGER,
    merkleroot VARCHAR(64),
    time INTEGER,
    nonce INTEGER,
    bits VARCHAR(8),
    difficulty REAL,
    chainwork VARCHAR(64),
    n_tx INTEGER,
    size INTEGER,
    weight INTEGER,
    previous_block_hash VARCHAR(64),
    next_block_hash VARCHAR(64),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

### Таблица `transactions`
```sql
CREATE TABLE transactions (
    id INTEGER PRIMARY KEY,
    txid VARCHAR(64) UNIQUE NOT NULL,
    block_hash VARCHAR(64),
    block_height INTEGER,
    version INTEGER,
    locktime INTEGER,
    size INTEGER,
    vsize INTEGER,
    weight INTEGER,
    fee INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (block_hash) REFERENCES blocks(hash)
);
```

### Таблица `transaction_inputs`
```sql
CREATE TABLE transaction_inputs (
    id INTEGER PRIMARY KEY,
    transaction_id INTEGER,
    vout INTEGER,
    prev_txid VARCHAR(64),
    script_sig TEXT,
    sequence INTEGER,
    FOREIGN KEY (transaction_id) REFERENCES transactions(id)
);
```

### Таблица `transaction_outputs`
```sql
CREATE TABLE transaction_outputs (
    id INTEGER PRIMARY KEY,
    transaction_id INTEGER,
    n INTEGER,
    value INTEGER,
    script_pubkey TEXT,
    address VARCHAR(64),
    FOREIGN KEY (transaction_id) REFERENCES transactions(id)
);
```

### Таблица `addresses`
```sql
CREATE TABLE addresses (
    id INTEGER PRIMARY KEY,
    address VARCHAR(64) UNIQUE NOT NULL,
    balance INTEGER DEFAULT 0,
    tx_count INTEGER DEFAULT 0,
    first_seen_block INTEGER,
    last_seen_block INTEGER,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);
```

## 5. API Endpoints

### Блоки
- `GET /api/blocks` - Список последних блоков (с пагинацией)
- `GET /api/blocks/{hash_or_height}` - Информация о блоке
- `GET /api/blocks/latest` - Последний блок
- `GET /api/blocks/{hash}/transactions` - Транзакции блока

### Транзакции
- `GET /api/transactions/{txid}` - Информация о транзакции
- `GET /api/transactions/latest` - Последние транзакции
- `GET /api/transactions/unconfirmed` - Неподтвержденные транзакции

### Адреса
- `GET /api/addresses/{address}` - Информация об адресе
- `GET /api/addresses/{address}/transactions` - Транзакции адреса
- `GET /api/addresses/{address}/utxos` - UTXO адреса

### Поиск
- `GET /api/search?q={query}` - Универсальный поиск
- `GET /api/stats` - Статистика сети

### Web Routes (HTMX)
- `GET /` - Главная страница
- `GET /block/{hash_or_height}` - Страница блока
- `GET /tx/{txid}` - Страница транзакции
- `GET /address/{address}` - Страница адреса
- `GET /search` - Страница поиска

## 6. Детальные этапы разработки

### Этап 1: Настройка окружения и структуры проекта
- [ ] Обновление `pyproject.toml` с зависимостями
- [ ] Создание структуры папок проекта
- [ ] Настройка виртуального окружения через uv
- [ ] Настройка базовой конфигурации

**Зависимости**:
```toml
dependencies = [
    "fastapi>=0.104.0",
    "uvicorn[standard]>=0.24.0",
    "sqlalchemy>=2.0.0",
    "alembic>=1.12.0",
    "pydantic>=2.5.0",
    "python-bitcoinrpc>=1.0",
    "jinja2>=3.1.0",
    "python-multipart>=0.0.6",
    "httpx>=0.25.0"
]
```

### Этап 2: Создание моделей данных
- [ ] Настройка SQLAlchemy и создание базовых моделей
- [ ] Создание Pydantic схем для API
- [ ] Настройка Alembic для миграций
- [ ] Создание первичной миграции

### Этап 3: Bitcoin RPC интеграция
- [ ] Создание Bitcoin RPC клиента
- [ ] Реализация методов получения блоков
- [ ] Реализация методов получения транзакций
- [ ] Обработка ошибок и reconnect логика

### Этап 4: Создание API endpoints
- [ ] Базовая настройка FastAPI приложения
- [ ] Endpoints для блоков
- [ ] Endpoints для транзакций
- [ ] Endpoints для адресов
- [ ] Поисковые endpoints
- [ ] Добавление пагинации и фильтрации

### Этап 5: Система синхронизации
- [ ] Background задача для синхронизации блоков
- [ ] Обработка reorg'ов (реорганизация блокчейна)
- [ ] Кэширование и оптимизация запросов
- [ ] Мониторинг состояния синхронизации

### Этап 6: Web интерфейс с HTMX
- [ ] Создание базовых HTML шаблонов
- [ ] Интеграция HTMX для динамических обновлений
- [ ] Главная страница с последними блоками
- [ ] Страницы блоков и транзакций
- [ ] Поиск в реальном времени
- [ ] Responsive дизайн и CSS стили

### Этап 7: Оптимизация и кэширование
- [ ] Добавление Redis для кэширования (опционально)
- [ ] Оптимизация SQL запросов
- [ ] Индексы для быстрого поиска
- [ ] Connection pooling для Bitcoin RPC

### Этап 8: Тестирование
- [ ] Unit тесты для сервисов
- [ ] Integration тесты для API
- [ ] E2E тесты для веб-интерфейса
- [ ] Нагрузочное тестирование

### Этап 9: Документация и развертывание
- [ ] API документация (автогенерация FastAPI)
- [ ] README с инструкциями по запуску
- [ ] Docker конфигурация
- [ ] Systemd сервисы для production

## 7. HTMX интеграция

### Ключевые возможности HTMX:
- **hx-get**: Автоматическое обновление блоков
- **hx-post**: Отправка поисковых запросов
- **hx-target**: Обновление конкретных частей страницы
- **hx-trigger**: Автообновление каждые 30 секунд
- **hx-swap**: Плавная замена контента

### Примеры использования:

```html
<!-- Автообновление списка блоков -->
<div hx-get="/api/blocks/latest" 
     hx-trigger="every 30s" 
     hx-target="#latest-blocks">
</div>

<!-- Поиск в реальном времени -->
<input type="text" 
       hx-get="/api/search" 
       hx-trigger="keyup changed delay:300ms" 
       hx-target="#search-results">

<!-- Пагинация без перезагрузки -->
<button hx-get="/api/blocks?page=2" 
        hx-target="#block-list" 
        hx-swap="outerHTML">
    Следующая страница
</button>
```

## 8. Конфигурация

### Bitcoin Core настройки (`bitcoin.conf`):
```ini
# RPC настройки
server=1
rpcuser=bitcoinrpc
rpcpassword=your_secure_password
rpcport=8332
rpcbind=127.0.0.1
rpcallowip=127.0.0.1

# Индексирование
txindex=1
blockfilterindex=1
```

### Настройки приложения:
```python
# app/config.py
class Settings:
    # Bitcoin RPC
    BITCOIN_RPC_HOST = "127.0.0.1"
    BITCOIN_RPC_PORT = 8332
    BITCOIN_RPC_USER = "bitcoinrpc"
    BITCOIN_RPC_PASSWORD = "your_secure_password"
    
    # Database
    DATABASE_URL = "sqlite:///./blockchain.db"
    
    # API
    API_V1_STR = "/api"
    PROJECT_NAME = "Bitcoin Explorer"
    
    # Cache
    CACHE_TTL = 300  # 5 minutes
```

## 9. Развертывание

### Development:
```bash
# Установка зависимостей через uv
uv install

# Активация виртуального окружения (если нужно)
source .venv/bin/activate  # Linux/Mac
# или
.venv\Scripts\activate     # Windows

# Запуск миграций
alembic upgrade head

# Запуск приложения
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Production (Docker):
```dockerfile
FROM python:3.12-slim

WORKDIR /app
COPY . .
RUN pip install -e .

EXPOSE 8000
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
```

## 10. Возможности для расширения

1. **WebSocket** для real-time обновлений
2. **GraphQL** API в дополнение к REST
3. **Mempool** анализ и визуализация
4. **Lightning Network** интеграция
5. **API rate limiting** и аутентификация
6. **Multi-currency** поддержка (Litecoin, etc.)
7. **Analytics dashboard** с графиками
8. **Mobile app** API endpoints

## 11. Безопасность

- Валидация всех входных данных
- Rate limiting для API endpoints
- CORS настройки для безопасных запросов
- Sanitization HTML контента
- Secure headers (HTTPS, CSP, etc.)

## 12. Мониторинг

- Логирование всех операций
- Health check endpoints
- Metrics сбор (Prometheus совместимый)
- Alerting при проблемах синхронизации

---

**Примерное время разработки**: 2-3 недели для MVP версии с базовым функционалом.

**Команда**: 1-2 разработчика

**Результат**: Полнофункциональный Bitcoin blockchain explorer с современным веб-интерфейсом и возможностями для дальнейшего расширения.
