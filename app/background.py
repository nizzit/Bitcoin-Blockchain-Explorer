"""
Background задачи для синхронизации блокчейна
"""

import asyncio
import logging
from contextlib import asynccontextmanager
from typing import AsyncGenerator

from fastapi import FastAPI

from app.database import SessionLocal
from app.services.sync_service import SyncService

logger = logging.getLogger(__name__)

# Глобальные переменные для управления задачами
_sync_task = None
_running = False


async def periodic_sync_task(interval: int = 60) -> None:
    """
    Периодическая задача синхронизации новых блоков

    Args:
        interval: Интервал между синхронизациями в секундах
    """
    global _running
    _running = True

    logger.info(f"Запущена периодическая синхронизация с интервалом {interval}с")

    while _running:
        try:
            # Создаем новую сессию БД для каждой итерации
            db = SessionLocal()
            try:
                sync_service = SyncService(db)

                # Проверяем на реорганизацию
                has_reorg = await sync_service.check_for_reorg()
                if has_reorg:
                    logger.warning("Обнаружена реорганизация блокчейна!")
                    # В реальной системе здесь нужно получить новый tip и обработать
                    # Пока просто логируем

                # Синхронизируем последние блоки если не идет другая синхронизация
                if not sync_service.is_syncing:
                    try:
                        result = await sync_service.sync_latest_blocks(max_blocks=100)
                        if result["synced_blocks"] > 0:
                            logger.info(
                                f"Автосинхронизация: блоков={result['synced_blocks']}, "
                                f"транзакций={result['synced_transactions']}"
                            )
                    except Exception as sync_error:
                        logger.error(f"Ошибка автосинхронизации: {sync_error}")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Ошибка в периодической задаче синхронизации: {e}")

        # Ждем до следующей итерации
        await asyncio.sleep(interval)

    logger.info("Периодическая синхронизация остановлена")


async def periodic_mempool_sync_task(interval: int = 30) -> None:
    """
    Периодическая задача синхронизации мемпула

    Args:
        interval: Интервал между синхронизациями в секундах
    """
    global _running

    logger.info(
        f"Запущена периодическая синхронизация мемпула с интервалом {interval}с"
    )

    while _running:
        try:
            db = SessionLocal()
            try:
                sync_service = SyncService(db)

                # Синхронизируем мемпул
                try:
                    result = await sync_service.sync_mempool()
                    if result["synced_transactions"] > 0:
                        logger.debug(
                            f"Автосинхронизация мемпула: "
                            f"транзакций={result['synced_transactions']}"
                        )
                except Exception as sync_error:
                    logger.error(f"Ошибка автосинхронизации мемпула: {sync_error}")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Ошибка в периодической задаче синхронизации мемпула: {e}")

        # Ждем до следующей итерации
        await asyncio.sleep(interval)

    logger.info("Периодическая синхронизация мемпула остановлена")


async def periodic_validation_task(interval: int = 3600) -> None:
    """
    Периодическая задача валидации целостности БД

    Args:
        interval: Интервал между проверками в секундах (по умолчанию 1 час)
    """
    global _running

    logger.info(
        f"Запущена периодическая валидация БД с интервалом {interval}с "
        f"({interval//60} мин)"
    )

    while _running:
        try:
            db = SessionLocal()
            try:
                sync_service = SyncService(db)

                # Валидация БД
                try:
                    result = sync_service.validate_database_integrity()
                    if not result["is_valid"]:
                        logger.warning(
                            f"Обнаружены проблемы целостности БД: {result['issues']}"
                        )
                    else:
                        logger.info("Валидация БД успешна")
                except Exception as validation_error:
                    logger.error(f"Ошибка валидации БД: {validation_error}")

            finally:
                db.close()

        except Exception as e:
            logger.error(f"Ошибка в периодической задаче валидации: {e}")

        # Ждем до следующей итерации
        await asyncio.sleep(interval)

    logger.info("Периодическая валидация БД остановлена")


async def start_background_tasks() -> None:
    """Запуск всех фоновых задач"""
    global _sync_task, _running

    if _sync_task is not None:
        logger.warning("Background задачи уже запущены")
        return

    _running = True

    # Создаем задачи
    tasks = [
        asyncio.create_task(periodic_sync_task(interval=10)),
        asyncio.create_task(periodic_mempool_sync_task(interval=10)),
        asyncio.create_task(periodic_validation_task(interval=3600)),
    ]

    _sync_task = asyncio.gather(*tasks, return_exceptions=True)

    logger.info("Все background задачи запущены")


async def stop_background_tasks() -> None:
    """Остановка всех фоновых задач"""
    global _sync_task, _running

    if _sync_task is None:
        logger.warning("Background задачи не запущены")
        return

    _running = False

    logger.info("Останавливаем background задачи...")

    try:
        # Даем время на завершение текущих операций
        await asyncio.sleep(2)

        # Отменяем задачи если они еще работают
        if not _sync_task.done():
            _sync_task.cancel()
            try:
                await _sync_task
            except asyncio.CancelledError:
                logger.info("Background задачи отменены")

    except Exception as e:
        logger.error(f"Ошибка при остановке background задач: {e}")

    finally:
        _sync_task = None
        logger.info("Background задачи остановлены")


@asynccontextmanager
async def lifespan(app: FastAPI) -> AsyncGenerator[None, None]:
    """
    Контекстный менеджер жизненного цикла приложения

    Запускает background задачи при старте приложения
    и останавливает их при завершении
    """
    # Startup
    logger.info("Запуск приложения...")

    try:
        # Запускаем background задачи
        await start_background_tasks()
        logger.info("Приложение запущено успешно")

        yield

    finally:
        # Shutdown
        logger.info("Остановка приложения...")
        await stop_background_tasks()
        logger.info("Приложение остановлено")
