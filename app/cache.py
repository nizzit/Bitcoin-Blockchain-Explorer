"""
Система кэширования для оптимизации запросов
"""

import hashlib
import logging
import time
from functools import wraps
from typing import Any, Callable, Dict, Optional

logger = logging.getLogger(__name__)


class SimpleCache:
    """Простая in-memory система кэширования"""

    def __init__(self, default_ttl: int = 300):
        """
        Инициализация кэша

        Args:
            default_ttl: Время жизни кэша по умолчанию в секундах
        """
        self._cache: Dict[str, Dict[str, Any]] = {}
        self._default_ttl = default_ttl

    def _generate_key(self, prefix: str, *args, **kwargs) -> str:
        """
        Генерация ключа кэша на основе аргументов

        Args:
            prefix: Префикс ключа
            *args: Позиционные аргументы
            **kwargs: Именованные аргументы

        Returns:
            Хеш ключа
        """
        # Создаем строку из аргументов
        key_parts = [prefix]
        key_parts.extend(str(arg) for arg in args)
        key_parts.extend(f"{k}={v}" for k, v in sorted(kwargs.items()))

        key_string = ":".join(key_parts)

        # Хешируем для создания короткого ключа
        return hashlib.md5(key_string.encode()).hexdigest()

    def get(self, key: str) -> Optional[Any]:
        """
        Получение значения из кэша

        Args:
            key: Ключ кэша

        Returns:
            Закэшированное значение или None если не найдено/истекло
        """
        if key not in self._cache:
            return None

        entry = self._cache[key]
        current_time = time.time()

        # Проверяем не истек ли TTL
        if current_time > entry["expires_at"]:
            del self._cache[key]
            return None

        logger.debug(f"Cache hit: {key}")
        return entry["value"]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> None:
        """
        Сохранение значения в кэш

        Args:
            key: Ключ кэша
            value: Значение для кэширования
            ttl: Время жизни в секундах (если None, используется default_ttl)
        """
        if ttl is None:
            ttl = self._default_ttl

        expires_at = time.time() + ttl

        self._cache[key] = {"value": value, "expires_at": expires_at}

        logger.debug(f"Cache set: {key} (TTL: {ttl}s)")

    def delete(self, key: str) -> bool:
        """
        Удаление значения из кэша

        Args:
            key: Ключ кэша

        Returns:
            True если ключ был удален, False если не найден
        """
        if key in self._cache:
            del self._cache[key]
            logger.debug(f"Cache delete: {key}")
            return True
        return False

    def clear(self) -> None:
        """Очистка всего кэша"""
        count = len(self._cache)
        self._cache.clear()
        logger.info(f"Cache cleared: {count} entries removed")

    def clear_expired(self) -> int:
        """
        Удаление истекших записей из кэша

        Returns:
            Количество удаленных записей
        """
        current_time = time.time()
        expired_keys = [
            key
            for key, entry in self._cache.items()
            if current_time > entry["expires_at"]
        ]

        for key in expired_keys:
            del self._cache[key]

        if expired_keys:
            logger.debug(f"Cleared {len(expired_keys)} expired cache entries")

        return len(expired_keys)

    def get_stats(self) -> Dict[str, Any]:
        """
        Получение статистики кэша

        Returns:
            Словарь со статистикой
        """
        current_time = time.time()
        total_entries = len(self._cache)
        expired_entries = sum(
            1 for entry in self._cache.values() if current_time > entry["expires_at"]
        )

        return {
            "total_entries": total_entries,
            "active_entries": total_entries - expired_entries,
            "expired_entries": expired_entries,
        }


# Глобальный экземпляр кэша
cache = SimpleCache(default_ttl=300)


def cached(ttl: int = 300, key_prefix: str = ""):
    """
    Декоратор для кэширования результатов функций

    Args:
        ttl: Время жизни кэша в секундах
        key_prefix: Префикс для ключа кэша

    Returns:
        Декорированная функция
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Генерируем ключ кэша
            prefix = key_prefix or func.__name__
            cache_key = cache._generate_key(prefix, *args, **kwargs)

            # Пытаемся получить из кэша
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Вызываем функцию и кэшируем результат
            result = func(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl)

            return result

        return wrapper

    return decorator


def cached_async(ttl: int = 300, key_prefix: str = ""):
    """
    Декоратор для кэширования результатов асинхронных функций

    Args:
        ttl: Время жизни кэша в секундах
        key_prefix: Префикс для ключа кэша

    Returns:
        Декорированная функция
    """

    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs):
            # Генерируем ключ кэша
            prefix = key_prefix or func.__name__
            cache_key = cache._generate_key(prefix, *args, **kwargs)

            # Пытаемся получить из кэша
            cached_value = cache.get(cache_key)
            if cached_value is not None:
                return cached_value

            # Вызываем функцию и кэшируем результат
            result = await func(*args, **kwargs)
            cache.set(cache_key, result, ttl=ttl)

            return result

        return wrapper

    return decorator


def invalidate_cache(key_prefix: str = "") -> None:
    """
    Инвалидация кэша по префиксу

    Args:
        key_prefix: Префикс ключа для инвалидации
    """
    if not key_prefix:
        cache.clear()
        return

    # Удаляем все ключи с указанным префиксом
    keys_to_delete = [key for key in cache._cache.keys() if key.startswith(key_prefix)]

    for key in keys_to_delete:
        cache.delete(key)

    logger.info(
        f"Invalidated {len(keys_to_delete)} cache entries with prefix: {key_prefix}"
    )
