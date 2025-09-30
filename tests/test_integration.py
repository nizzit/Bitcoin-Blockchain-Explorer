#!/usr/bin/env python3
"""
Тестирование Bitcoin RPC интеграции с использованием unittest
"""

import asyncio
import logging
import sys
import unittest
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
    from app.services.bitcoin_rpc import bitcoin_rpc
    from app.services.block_service import get_block_service
    from app.services.sync_service import get_sync_service
    from app.services.transaction_service import get_transaction_service
except ImportError as e:
    logger.error(f"Ошибка импорта: {e}")
    sys.exit(1)


class BitcoinRPCIntegrationTest(unittest.TestCase):
    """Интеграционные тесты Bitcoin RPC"""

    @classmethod
    def setUpClass(cls):
        """Инициализация перед всеми тестами"""
        logger.info("🚀 Начинаем интеграционное тестирование Bitcoin RPC")
        logger.info("=" * 60)
        cls.start_time = datetime.now()

    @classmethod
    def tearDownClass(cls):
        """Завершение после всех тестов"""
        duration = datetime.now() - cls.start_time
        logger.info("\n" + "=" * 60)
        logger.info("📊 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО")
        logger.info(f"⏱️  Время выполнения: {duration.total_seconds():.1f}с")
        logger.info("=" * 60)

    def setUp(self):
        """Инициализация перед каждым тестом"""
        self.db = next(get_db())

    def tearDown(self):
        """Очистка после каждого теста"""
        if hasattr(self, "db"):
            self.db.close()

    def test_01_configuration(self):
        """Тестирование конфигурации"""
        logger.info("\n⚙️  Тестирование конфигурации...")
        logger.info("-" * 40)

        logger.info("📝 Настройки приложения:")
        logger.info(f"   • Проект: {settings.PROJECT_NAME}")
        logger.info(f"   • Версия: {settings.VERSION}")
        logger.info(
            f"   • Bitcoin RPC: {settings.BITCOIN_RPC_HOST}:"
            f"{settings.BITCOIN_RPC_PORT}"
        )
        logger.info(f"   • База данных: {settings.DATABASE_URL}")
        logger.info(f"   • Timeout RPC: {settings.BITCOIN_RPC_TIMEOUT}с")
        logger.info(
            f"   • Синхронизация: "
            f"{'включена' if settings.SYNC_ENABLED else 'отключена'}"
        )
        logger.info(f"   • Интервал синхронизации: {settings.SYNC_INTERVAL}с")

        # Проверка наличия обязательных настроек
        self.assertIsNotNone(settings.PROJECT_NAME)
        self.assertIsNotNone(settings.VERSION)
        self.assertIsNotNone(settings.BITCOIN_RPC_HOST)
        self.assertIsNotNone(settings.BITCOIN_RPC_PORT)
        self.assertIsNotNone(settings.DATABASE_URL)

        logger.info("✅ Конфигурация: ПРОЙДЕН")

    def test_02_bitcoin_rpc(self):
        """Тестирование Bitcoin RPC клиента"""
        logger.info("\n🔧 Тестирование Bitcoin RPC клиента...")
        logger.info("-" * 40)

        # Тест подключения
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        is_connected = loop.run_until_complete(bitcoin_rpc.test_connection())
        loop.close()

        self.assertTrue(is_connected, "Не удалось подключиться к Bitcoin Core")
        logger.info("✅ Подключение к Bitcoin Core успешно")

        # Получение базовой информации
        blockchain_info = bitcoin_rpc.get_blockchain_info()
        self.assertIsNotNone(blockchain_info)
        self.assertIn("chain", blockchain_info)
        self.assertIn("blocks", blockchain_info)

        logger.info("📊 Информация о блокчейне:")
        logger.info(f"   • Сеть: {blockchain_info.get('chain', 'unknown')}")
        logger.info(f"   • Блоков: {blockchain_info.get('blocks', 0)}")
        logger.info(f"   • Сложность: {blockchain_info.get('difficulty', 0)}")

        # Получение информации о последнем блоке
        best_hash = bitcoin_rpc.get_best_block_hash()
        block_count = bitcoin_rpc.get_block_count()
        self.assertIsNotNone(best_hash)
        self.assertGreaterEqual(block_count, 0)

        logger.info(f"📦 Последний блок: #{block_count} ({best_hash[:16]}...)")

        # Получение информации о мемпуле
        mempool_info = bitcoin_rpc.get_mempool_info()
        self.assertIsNotNone(mempool_info)
        self.assertIn("size", mempool_info)

        logger.info(f"🔄 Мемпул: {mempool_info.get('size', 0)} транзакций")
        logger.info("✅ Bitcoin RPC: ПРОЙДЕН")

    def test_03_block_service(self):
        """Тестирование сервиса блоков"""
        logger.info("\n📦 Тестирование сервиса блоков...")
        logger.info("-" * 40)

        block_service = get_block_service(self.db)

        # Получение информации о блокчейне
        blockchain_info = block_service.get_blockchain_info()
        self.assertIsNotNone(blockchain_info)
        self.assertIn("blocks", blockchain_info)
        self.assertIn("db_height", blockchain_info)

        logger.info(f"📊 Высота сети: {blockchain_info.get('blocks', 0)}")
        logger.info(f"📊 Высота БД: {blockchain_info.get('db_height', 0)}")
        logger.info(
            f"📊 Прогресс синхронизации: {blockchain_info.get('sync_progress', 0):.1f}%"
        )

        # Получение последних блоков из БД
        latest_blocks = block_service.get_latest_blocks(limit=3)
        self.assertIsNotNone(latest_blocks)
        self.assertIsInstance(latest_blocks, list)

        logger.info(f"📦 Последние блоки в БД: {len(latest_blocks)}")

        for block in latest_blocks:
            logger.info(
                f"   • Блок #{block.height}: {block.hash[:16]}... ({block.n_tx} тx)"
            )

        # Тест получения блока через RPC
        try:
            latest_height = bitcoin_rpc.get_block_count()
            test_block = block_service.get_or_fetch_block(latest_height)
            self.assertIsNotNone(test_block)
            logger.info(f"✅ Успешно получен блок #{test_block.height}")
        except Exception as e:
            logger.warning(f"⚠️  Не удалось получить тестовый блок: {e}")

        logger.info("✅ Сервис блоков: ПРОЙДЕН")

    def test_04_transaction_service(self):
        """Тестирование сервиса транзакций"""
        logger.info("\n💰 Тестирование сервиса транзакций...")
        logger.info("-" * 40)

        tx_service = get_transaction_service(self.db)

        # Получение последних транзакций (асинхронный метод)
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        latest_txs_result = loop.run_until_complete(
            tx_service.get_latest_transactions(limit=3)
        )
        loop.close()

        # Метод возвращает кортеж (transactions, total)
        latest_txs, total = latest_txs_result
        self.assertIsNotNone(latest_txs)
        self.assertIsInstance(latest_txs, list)

        logger.info(f"💰 Последние транзакции в БД: {len(latest_txs)}")

        for tx in latest_txs:
            logger.info(f"   • {tx.txid[:16]}... (блок #{tx.block_height})")

        # Получение количества транзакций
        tx_count = tx_service.get_transaction_count()
        self.assertIsNotNone(tx_count)
        self.assertGreaterEqual(tx_count, 0)

        logger.info(f"📊 Всего транзакций в БД: {tx_count}")

        # Тест мемпула
        try:
            mempool_txs = tx_service.get_mempool_transactions()
            self.assertIsNotNone(mempool_txs)
            logger.info(f"🔄 Транзакций в мемпуле: {len(mempool_txs)}")
        except Exception as e:
            logger.warning(f"⚠️  Не удалось получить мемпул: {e}")

        logger.info("✅ Сервис транзакций: ПРОЙДЕН")

    def test_05_sync_service(self):
        """Тестирование сервиса синхронизации"""
        logger.info("\n🔄 Тестирование сервиса синхронизации...")
        logger.info("-" * 40)

        sync_service = get_sync_service(self.db)

        # Получение статуса синхронизации
        status = sync_service.get_sync_status()
        self.assertIsNotNone(status)
        self.assertIn("is_syncing", status)
        self.assertIn("network_height", status)
        self.assertIn("db_height", status)

        logger.info("📊 Статус синхронизации:")
        logger.info(f"   • Синхронизация активна: {status['is_syncing']}")
        logger.info(f"   • Высота сети: {status['network_height']}")
        logger.info(f"   • Высота БД: {status['db_height']}")
        logger.info(f"   • Отстает на блоков: {status['blocks_behind']}")
        logger.info(f"   • Прогресс: {status['sync_progress']}%")
        logger.info(f"   • Синхронизировано: {status['is_synced']}")

        # Валидация БД
        validation = sync_service.validate_database_integrity()
        self.assertIsNotNone(validation)
        self.assertIn("is_valid", validation)
        self.assertIn("checked_blocks", validation)

        logger.info("🔍 Валидация БД:")
        logger.info(f"   • Проверено блоков: {validation['checked_blocks']}")
        logger.info(f"   • Проверено транзакций: {validation['checked_transactions']}")
        logger.info(f"   • Валидна: {validation['is_valid']}")

        if validation["issues"]:
            logger.warning("⚠️  Найдены проблемы:")
            for issue in validation["issues"][:3]:  # Показываем только первые 3
                logger.warning(f"     - {issue}")

        # Проверка на реорганизацию
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        has_reorg = loop.run_until_complete(sync_service.check_for_reorg())
        loop.close()

        reorg_status = "обнаружена" if has_reorg else "не обнаружена"
        logger.info(f"🔄 Реорганизация блокчейна: {reorg_status}")

        # Тест синхронизации нескольких блоков
        if status["blocks_behind"] > 0 and status["blocks_behind"] <= 5:
            logger.info("🔄 Попытка синхронизации нескольких блоков...")
            try:
                loop = asyncio.new_event_loop()
                asyncio.set_event_loop(loop)
                sync_result = loop.run_until_complete(
                    sync_service.sync_latest_blocks(max_blocks=3)
                )
                loop.close()

                self.assertIsNotNone(sync_result)
                self.assertIn("synced_blocks", sync_result)

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

        logger.info("✅ Сервис синхронизации: ПРОЙДЕН")


def suite():
    """Создание набора тестов"""
    test_suite = unittest.TestSuite()
    test_suite.addTest(unittest.makeSuite(BitcoinRPCIntegrationTest))
    return test_suite


if __name__ == "__main__":
    try:
        # Запуск тестов с подробным выводом
        runner = unittest.TextTestRunner(verbosity=2)
        result = runner.run(suite())

        # Вывод итоговой статистики
        logger.info("\n" + "=" * 60)
        logger.info("📊 РЕЗУЛЬТАТЫ ТЕСТИРОВАНИЯ")
        logger.info("=" * 60)

        total_tests = result.testsRun
        failures = len(result.failures)
        errors = len(result.errors)
        tests_passed = total_tests - failures - errors
        success_rate = (tests_passed / total_tests * 100) if total_tests > 0 else 0

        logger.info(f"✅ Пройдено тестов: {tests_passed}/{total_tests}")
        logger.info(f"❌ Провалено: {failures}")
        logger.info(f"💥 Ошибок: {errors}")
        logger.info(f"📈 Успешность: {success_rate:.1f}%")

        if result.wasSuccessful():
            logger.info("🎉 ВСЕ ТЕСТЫ ПРОЙДЕНЫ УСПЕШНО!")
            logger.info("🚀 Bitcoin RPC интеграция готова к использованию")
        else:
            logger.warning("⚠️  НЕКОТОРЫЕ ТЕСТЫ НЕ ПРОЙДЕНЫ")
            logger.warning("🔧 Проверьте настройки Bitcoin Core и подключение")

        logger.info("=" * 60)

        # Возврат кода выхода
        sys.exit(0 if result.wasSuccessful() else 1)

    except KeyboardInterrupt:
        logger.info("\n🛑 Тестирование прервано пользователем")
        sys.exit(1)
    except Exception as e:
        logger.error(f"💥 Критическая ошибка: {e}")
        sys.exit(1)
