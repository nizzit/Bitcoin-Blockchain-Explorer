"""
API endpoints для управления кэшем
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, HTTPException

from app.cache import cache, invalidate_cache

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/cache", tags=["cache"])


@router.get("/stats")
async def get_cache_stats() -> Dict[str, Any]:
    """
    Получение статистики кэша

    Returns:
        Статистика использования кэша
    """
    try:
        stats = cache.get_stats()
        return {
            "status": "success",
            "stats": stats,
        }
    except Exception as e:
        logger.error(f"Ошибка получения статистики кэша: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/clear")
async def clear_cache(prefix: str = "") -> Dict[str, Any]:
    """
    Очистка кэша

    Args:
        prefix: Префикс для выборочной очистки (если пусто - очищается весь кэш)

    Returns:
        Результат очистки
    """
    try:
        if prefix:
            invalidate_cache(prefix)
            message = f"Кэш очищен для префикса: {prefix}"
        else:
            cache.clear()
            message = "Весь кэш очищен"

        logger.info(message)

        return {
            "status": "success",
            "message": message,
        }
    except Exception as e:
        logger.error(f"Ошибка очистки кэша: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/clear-expired")
async def clear_expired_cache() -> Dict[str, Any]:
    """
    Очистка истекших записей из кэша

    Returns:
        Количество удаленных записей
    """
    try:
        removed_count = cache.clear_expired()

        return {
            "status": "success",
            "removed_entries": removed_count,
            "message": f"Удалено истекших записей: {removed_count}",
        }
    except Exception as e:
        logger.error(f"Ошибка очистки истекших записей: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")
