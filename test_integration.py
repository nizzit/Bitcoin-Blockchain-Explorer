#!/usr/bin/env python3
"""
Тестирование Bitcoin RPC интеграции
"""

import asyncio
import logging
import sys
from datetime import datetime

# Настройка логирования
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)

# Импорты приложения
try:
    from app.config import settings
    from app.database import get_db
    from app.services.bitcoin_rpc import BitcoinRPCError, bitcoin_rpc
    from app.services.block_service import get_block_service
    from app.services.sync_service import get_sync_service
    from app.services.transaction_service import get_transaction_service
except ImportError as e:
    logger.error(f"Ошибка импорта: {e}")
    sys.exit(1)


async def test_bitcoin_rpc():
    """Тестирование Bitcoin RPC клиента"""
    logger.info("🔧 Тестирование Bitcoin RPC клиента...")

    try:
        # Тест подключения
        is_connected = await bitcoin_rpc.test_connection()
        if not is_connected:
            logger.error("❌ Не удалось подключиться к Bitcoin Core")
            return False

        logger.info("✅ Подключение к Bitcoin Core успешно")

        # Получение базовой информации
        blockchain_info = bitcoin_rpc.get_blockchain_info()
        logger.info("📊 Информация о блокчейне:")
        logger.info(f"   • Сеть: {blockchain_info.get('chain', 'unknown')}")
        logger.info(f"   • Блоков: {blockchain_info.get('blocks', 0)}")
        logger.info(f"   • Сложность: {blockchain_info.get('difficulty', 0)}")

        # Получение информации о последнем блоке
        best_hash = bitcoin_rpc.get_best_block_hash()
        block_count = bitcoin_rpc.get_block_count()
        logger.info(f"📦 Последний блок: #{block_count} ({best_hash[:16]}...)")

        # Получение информации о мемпуле
        mempool_info = bitcoin_rpc.get_mempool_info()
        logger.info(f"🔄 Мемпул: {mempool_info.get('size', 0)} транзакций")

        return True

    except BitcoinRPCError as e:
        logger.error(f"❌ RPC ошибка: {e}")
        return False
    except Exception as e:
        logger.error(f"❌ Неожиданная ошибка: {e}")
        return False


def test_block_service():
    """Тестирование сервиса блоков"""
    logger.info("📦 Тестирование сервиса блоков...")

    try:
        db = next(get_db())
        block_service = get_block_service(db)

        # Получение информации о блокчейне
        blockchain_info = block_service.get_blockchain_info()
        logger.info(f"📊 Высота сети: {blockchain_info.get('blocks', 0)}")
        logger.info(f"📊 Высота БД: {blockchain_info.get('db_height', 0)}")
        logger.info(
            f"📊 Прогресс синхронизации: {blockchain_info.get('sync_progress', 0):.1f}%"
        )

        # Получение последних блоков из БД
        latest_blocks = block_service.get_latest_blocks(limit=3)
        logger.info(f"📦 Последние блоки в БД: {len(latest_blocks)}")

        for block in latest_blocks:
            logger.info(
                f"   • Блок #{block.height}: {block.hash[:16]}... ({block.n_tx} тx)"
            )

        # Тест получения блока через RPC
        try:
            latest_height = bitcoin_rpc.get_block_count()
            test_block = block_service.get_or_fetch_block(latest_height)
            logger.info(f"✅ Успешно получен блок #{test_block.height}")
        except Exception as e:
            logger.warning(f"⚠️  Не удалось получить тестовый блок: {e}")

        return True

    except Exception as e:
        logger.error(f"❌ Ошибка тестирования блоков: {e}")
        return False


def test_transaction_service():
    """Тестирование сервиса транзакций"""
    logger.info("💰 Тестирование сервиса транзакций...")

    try:
        db = next(get_db())
        tx_service = get_transaction_service(db)

        # Получение последних транзакций
        latest_txs = tx_service.get_latest_transactions(limit=3)
        logger.info(f"💰 Последние транзакции в БД: {len(latest_txs)}")

        for tx in latest_txs:
            logger.info(f"   • {tx.txid[:16]}... (блок #{tx.block_height})")

        # Получение количества транзакций
        tx_count = tx_service.get_transaction_count()
        logger.info(f"📊 Всего транзакций в БД: {tx_count}")

        # Тест мемпула
        try:
            mempool_txs = tx_service.get_mempool_transactions()
            logger.info(f"🔄 Транзакций в мемпуле: {len(mempool_txs)}")
        except Exception as e:
            logger.warning(f"⚠️  Не удалось получить мемпул: {e}")

        return True

    except Exception as e:
        logger.error(f"❌ Ошибка тестирования транзакций: {e}")
        return False


async def test_sync_service():
    """Тестирование сервиса синхронизации"""
    logger.info("🔄 Тестирование сервиса синхронизации...")

    try:
        db = next(get_db())
        sync_service = get_sync_service(db)

        # Получение статуса синхронизации
        status = sync_service.get_sync_status()
        logger.info("📊 Статус синхронизации:")
        logger.info(f"   • Синхронизация активна: {status['is_syncing']}")
        logger.info(f"   • Высота сети: {status['network_height']}")
        logger.info(f"   • Высота БД: {status['db_height']}")
        logger.info(f"   • Отстает на блоков: {status['blocks_behind']}")
        logger.info(f"   • Прогресс: {status['sync_progress']}%")
        logger.info(f"   • Синхронизировано: {status['is_synced']}")

        # Валидация БД
        validation = sync_service.validate_database_integrity()
        logger.info("🔍 Валидация БД:")
        logger.info(f"   • Проверено блоков: {validation['checked_blocks']}")
        logger.info(f"   • Проверено транзакций: {validation['checked_transactions']}")
        logger.info(f"   • Валидна: {validation['is_valid']}")

        if validation["issues"]:
            logger.warning("⚠️  Найдены проблемы:")
            for issue in validation["issues"][:3]:  # Показываем только первые 3
                logger.warning(f"     - {issue}")

        # Проверка на реорганизацию
        has_reorg = await sync_service.check_for_reorg()
        reorg_status = "обнаружена" if has_reorg else "не обнаружена"
        logger.info(f"🔄 Реорганизация блокчейна: {reorg_status}")

        # Тест синхронизации нескольких блоков
        if status["blocks_behind"] > 0 and status["blocks_behind"] <= 5:
            logger.info("🔄 Попытка синхронизации нескольких блоков...")
            try:
                sync_result = await sync_service.sync_latest_blocks(max_blocks=3)
                logger.info("✅ Синхронизировано:")
                logger.info(f"   • Блоков: {sync_result['synced_blocks']}")
                logger.info(f"   • Транзакций: {sync_result['synced_transactions']}")
                logger.info(f"   • Ошибок: {sync_result['errors']}")
            except Exception as e:
                logger.warning(f"⚠️  Не удалось синхронизировать блоки: {e}")
        else:
            logger.info(
                "ℹ️  Пропускаем тест синхронизации "
                "(слишком много блоков или уже синхронизировано)"
            )

        return True

    except Exception as e:
        logger.error(f"❌ Ошибка тестирования синхронизации: {e}")
        return False


def test_configuration():
    """Тестирование конфигурации"""
    logger.info("⚙️  Тестирование конфигурации...")

    logger.info("📝 Настройки приложения:")
    logger.info(f"   • Проект: {settings.PROJECT_NAME}")
    logger.info(f"   • Версия: {settings.VERSION}")
    logger.info(
        f"   • Bitcoin RPC: {settings.BITCOIN_RPC_HOST}:{settings.BITCOIN_RPC_PORT}"
    )
    logger.info(f"   • База данных: {settings.DATABASE_URL}")
    logger.info(f"   • Timeout RPC: {settings.BITCOIN_RPC_TIMEOUT}с")
    logger.info(
        f"   • Синхронизация: {'включена' if settings.SYNC_ENABLED else 'отключена'}"
    )
    logger.info(f"   • Интервал синхронизации: {settings.SYNC_INTERVAL}с")

    return True


async def main():
    """Основная функция тестирования"""
    logger.info("🚀 Начинаем интеграционное тестирование Bitcoin RPC")
    logger.info("=" * 60)

    start_time = datetime.now()
    tests_passed = 0
    total_tests = 5

    # Список тестов
    tests = [
        ("Конфигурация", test_configuration),
        ("Bitcoin RPC", test_bitcoin_rpc),
        ("Сервис блоков", test_block_service),
        ("Сервис транзакций", test_transaction_service),
        ("Сервис синхронизации", test_sync_service),
    ]

    # Выполнение тестов
    for test_name, test_func in tests:
        logger.info(f"\n📋 Тест: {test_name}")
        logger.info("-" * 40)

        try:
            if asyncio.iscoroutinefunction(test_func):
                result = await test_func()
            else:
                result = test_func()

            if result:
                tests_passed += 1
                logger.info(f"✅ {test_name}: ПРОЙДЕН")
            else:
                logger.error(f"❌ {test_name}: ПРОВАЛЕН")

        except Exception as e:
            logger.error(f"❌ {test_name}: ОШИБКА - {e}")

    # Итоговые результаты
    logger.info("\n" + "=" * 60)
    logger.info("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
    logger.info("=" * 60)

    duration = datetime.now() - start_time
    success_rate = (tests_passed / total_tests) * 100

    logger.info(f"✅ Пройдено тестов: {tests_passed}/{total_tests}")
    logger.info(f"📈 Успешность: {success_rate:.1f}%")
    logger.info(f"⏱️  Время выполнения: {duration.total_seconds():.1f}с")

    if tests_passed == total_tests:
        logger.info("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
        logger.info("🚀 Bitcoin RPC интеграция готова к использованию")
    else:
        logger.warning("⚠️  НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
        logger.warning("🔧 Проверьте настройки Bitcoin Core и подключение")

    logger.info("=" * 60)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logger.info("\n🛑 Тестирование прервано пользователем")
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        sys.exit(1)
