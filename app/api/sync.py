"""
API endpoints для управления синхронизацией
"""

import logging
from typing import Any, Dict

from fastapi import APIRouter, BackgroundTasks, Depends, HTTPException
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.sync_service import SyncService, SyncServiceError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/sync", tags=["sync"])


@router.get("/status")
async def get_sync_status(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Получение статуса синхронизации

    Returns:
        Статус синхронизации с блокчейном
    """
    try:
        sync_service = SyncService(db)
        status = sync_service.get_sync_status()
        return status
    except SyncServiceError as e:
        logger.error(f"Ошибка получения статуса: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Непредвиденная ошибка: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/start")
async def start_sync(
    background_tasks: BackgroundTasks,
    max_blocks: int = 100,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Запуск синхронизации последних блоков

    Args:
        max_blocks: Максимальное количество блоков для синхронизации
        background_tasks: Background tasks для асинхронного выполнения

    Returns:
        Статус запуска синхронизации
    """
    try:
        sync_service = SyncService(db)

        # Проверяем, не идет ли уже синхронизация
        if sync_service.is_syncing:
            raise HTTPException(status_code=409, detail="Синхронизация уже выполняется")

        # Добавляем задачу синхронизации в background
        async def sync_task():
            try:
                result = await sync_service.sync_latest_blocks(max_blocks=max_blocks)
                logger.info(f"Синхронизация завершена: {result}")
            except Exception as e:
                logger.error(f"Ошибка в background синхронизации: {e}")

        background_tasks.add_task(sync_task)

        return {
            "status": "started",
            "message": f"Запущена синхронизация до {max_blocks} блоков",
            "max_blocks": max_blocks,
        }

    except SyncServiceError as e:
        logger.error(f"Ошибка запуска синхронизации: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Непредвиденная ошибка: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/full")
async def start_full_sync(
    background_tasks: BackgroundTasks,
    batch_size: int = 100,
    db: Session = Depends(get_db),
) -> Dict[str, Any]:
    """
    Запуск полной синхронизации с блокчейном

    Args:
        batch_size: Размер батча для синхронизации
        background_tasks: Background tasks для асинхронного выполнения

    Returns:
        Статус запуска полной синхронизации
    """
    try:
        sync_service = SyncService(db)

        # Проверяем, не идет ли уже синхронизация
        if sync_service.is_syncing:
            raise HTTPException(status_code=409, detail="Синхронизация уже выполняется")

        # Добавляем задачу полной синхронизации в background
        async def full_sync_task():
            try:
                result = await sync_service.full_sync(batch_size=batch_size)
                logger.info(f"Полная синхронизация завершена: {result}")
            except Exception as e:
                logger.error(f"Ошибка в background полной синхронизации: {e}")

        background_tasks.add_task(full_sync_task)

        return {
            "status": "started",
            "message": "Запущена полная синхронизация",
            "batch_size": batch_size,
        }

    except SyncServiceError as e:
        logger.error(f"Ошибка запуска полной синхронизации: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Непредвиденная ошибка: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/mempool")
async def sync_mempool(
    background_tasks: BackgroundTasks, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Синхронизация транзакций из мемпула

    Returns:
        Статус запуска синхронизации мемпула
    """
    try:
        sync_service = SyncService(db)

        # Добавляем задачу синхронизации мемпула в background
        async def mempool_sync_task():
            try:
                result = await sync_service.sync_mempool()
                logger.info(f"Синхронизация мемпула завершена: {result}")
            except Exception as e:
                logger.error(f"Ошибка в background синхронизации мемпула: {e}")

        background_tasks.add_task(mempool_sync_task)

        return {"status": "started", "message": "Запущена синхронизация мемпула"}

    except SyncServiceError as e:
        logger.error(f"Ошибка запуска синхронизации мемпула: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Непредвиденная ошибка: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/check-reorg")
async def check_for_reorg(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Проверка на реорганизацию блокчейна

    Returns:
        Результат проверки на реорганизацию
    """
    try:
        sync_service = SyncService(db)
        has_reorg = await sync_service.check_for_reorg()

        return {
            "has_reorg": has_reorg,
            "message": (
                "Обнаружена реорганизация"
                if has_reorg
                else "Реорганизация не обнаружена"
            ),
        }

    except Exception as e:
        logger.error(f"Ошибка проверки реорганизации: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.post("/handle-reorg")
async def handle_reorg(
    new_tip_hash: str, db: Session = Depends(get_db)
) -> Dict[str, Any]:
    """
    Обработка реорганизации блокчейна

    Args:
        new_tip_hash: Хеш нового верхнего блока

    Returns:
        Результат обработки реорганизации
    """
    try:
        sync_service = SyncService(db)
        result = sync_service.handle_reorg(new_tip_hash)

        return result

    except SyncServiceError as e:
        logger.error(f"Ошибка обработки реорганизации: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Непредвиденная ошибка: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/validate")
async def validate_database(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Валидация целостности базы данных

    Returns:
        Результат валидации
    """
    try:
        sync_service = SyncService(db)
        result = sync_service.validate_database_integrity()

        return result

    except SyncServiceError as e:
        logger.error(f"Ошибка валидации БД: {e}")
        raise HTTPException(status_code=500, detail=str(e))
    except Exception as e:
        logger.error(f"Непредвиденная ошибка: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")


@router.get("/stats")
async def get_sync_stats(db: Session = Depends(get_db)) -> Dict[str, Any]:
    """
    Получение статистики синхронизации

    Returns:
        Статистика синхронизации
    """
    try:
        sync_service = SyncService(db)
        stats = sync_service.sync_stats

        return stats

    except Exception as e:
        logger.error(f"Ошибка получения статистики: {e}")
        raise HTTPException(status_code=500, detail="Внутренняя ошибка сервера")
