"""
Конфигурация приложения Bitcoin Blockchain Explorer
"""

from pydantic_settings import BaseSettings


class Settings(BaseSettings):
    """Настройки приложения"""

    # Общие настройки
    PROJECT_NAME: str = "Bitcoin Blockchain Explorer"
    VERSION: str = "0.1.0"
    API_V1_STR: str = "/api"

    # База данных
    DATABASE_URL: str = "sqlite:///./blockchain.db"

    # Bitcoin RPC настройки
    BITCOIN_RPC_HOST: str = "127.0.0.1"
    BITCOIN_RPC_PORT: int = 18445
    BITCOIN_RPC_USER: str = "bitcoinrpc"
    BITCOIN_RPC_PASSWORD: str = "your_secure_password"
    BITCOIN_RPC_TIMEOUT: int = 30

    # API настройки
    CACHE_TTL: int = 300  # 5 минут
    MAX_BLOCKS_PER_PAGE: int = 50
    MAX_TRANSACTIONS_PER_PAGE: int = 100

    # CORS настройки
    BACKEND_CORS_ORIGINS: list[str] = ["http://localhost:8000"]

    # Синхронизация
    SYNC_ENABLED: bool = True
    SYNC_INTERVAL: int = 30  # секунды

    # Debug режим
    DEBUG: bool = False

    class Config:
        env_file = ".env"
        case_sensitive = True


# Глобальный экземпляр настроек
settings = Settings()
