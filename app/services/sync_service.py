"""
Сервис синхронизации с Bitcoin блокчейном
"""

import asyncio
import logging
from typing import Any, Dict

from sqlalchemy.orm import Session

from app.database import get_db
from app.models.block import Block
from app.models.transaction import Transaction
from app.services.bitcoin_rpc import BitcoinRPCError, bitcoin_rpc
from app.services.block_service import BlockService
from app.services.transaction_service import TransactionService

logger = logging.getLogger(__name__)


class SyncServiceError(Exception):
    """Исключение для ошибок сервиса синхронизации"""

    pass


class SyncService:
    """Сервис синхронизации с Bitcoin блокчейном"""

    def __init__(self, db: Session):
        self.db = db
        self.block_service = BlockService(db)
        self.transaction_service = TransactionService(db)
        self._is_syncing = False
        self._sync_stats = {
            "blocks_synced": 0,
            "transactions_synced": 0,
            "errors": 0,
            "last_sync_time": None,
            "sync_progress": 0.0,
        }

    @property
    def is_syncing(self) -> bool:
        """Проверка, идет ли синхронизация"""
        return self._is_syncing

    @property
    def sync_stats(self) -> Dict[str, Any]:
        """Получение статистики синхронизации"""
        return self._sync_stats.copy()

    def get_sync_status(self) -> Dict[str, Any]:
        """
        Получение статуса синхронизации

        Returns:
            Словарь с информацией о состоянии синхронизации
        """
        try:
            # Получаем информацию из Bitcoin Core
            blockchain_info = bitcoin_rpc.get_blockchain_info()
            network_height = blockchain_info.get("blocks", 0)

            # Получаем высоту последнего блока в БД
            db_height = self.block_service.get_latest_block_height()

            # Вычисляем прогресс
            if network_height > 0:
                progress = (db_height / network_height) * 100
            else:
                progress = 0

            status = {
                "is_syncing": self._is_syncing,
                "network_height": network_height,
                "db_height": db_height,
                "blocks_behind": max(0, network_height - db_height),
                "sync_progress": round(progress, 2),
                "is_synced": abs(network_height - db_height) <= 1,
                "stats": self._sync_stats,
                "blockchain_info": blockchain_info,
            }

            return status

        except Exception as e:
            logger.error(f"Ошибка получения статуса синхронизации: {e}")
            raise SyncServiceError(f"Не удалось получить статус синхронизации: {e}")

    async def sync_latest_blocks(self, max_blocks: int = 10) -> Dict[str, Any]:
        """
        Синхронизация последних блоков

        Args:
            max_blocks: Максимальное количество блоков для синхронизации

        Returns:
            Результат синхронизации
        """
        if self._is_syncing:
            raise SyncServiceError("Синхронизация уже выполняется")

        self._is_syncing = True
        synced_blocks = 0
        synced_transactions = 0
        errors = 0

        try:
            # Получаем текущую высоту блокчейна
            network_height = bitcoin_rpc.get_block_count()
            db_height = self.block_service.get_latest_block_height()

            logger.info(
                f"Начинаем синхронизацию: сеть={network_height}, БД={db_height}"
            )

            # Определяем блоки для синхронизации
            start_height = db_height + 1
            end_height = min(start_height + max_blocks - 1, network_height)

            if start_height > network_height:
                logger.info("База данных уже синхронизирована")
                return {
                    "synced_blocks": 0,
                    "synced_transactions": 0,
                    "errors": 0,
                    "message": "Уже синхронизировано",
                }

            # Синхронизируем блоки
            for height in range(start_height, end_height + 1):
                try:
                    # Получаем блок через RPC
                    block_data = self.block_service.fetch_block_from_rpc(height)

                    # Сохраняем блок
                    self.block_service.save_block_to_db(block_data)
                    synced_blocks += 1

                    # Сохраняем транзакции блока
                    if "tx" in block_data:
                        for tx_data in block_data["tx"]:
                            if isinstance(tx_data, str):
                                # Если tx - это только txid, получаем полные данные
                                try:
                                    full_tx_data = bitcoin_rpc.get_raw_transaction(
                                        tx_data, verbose=True
                                    )
                                    self.transaction_service.save_transaction_to_db(
                                        full_tx_data
                                    )
                                    synced_transactions += 1
                                except Exception as tx_error:
                                    logger.warning(
                                        f"Ошибка синхронизации транзакции {tx_data}: "
                                        f"{tx_error}"
                                    )
                                    errors += 1
                            else:
                                # Уже полные данные транзакции
                                try:
                                    self.transaction_service.save_transaction_to_db(
                                        tx_data
                                    )
                                    synced_transactions += 1
                                except Exception as tx_error:
                                    logger.warning(
                                        f"Ошибка синхронизации транзакции: {tx_error}"
                                    )
                                    errors += 1

                    logger.info(f"Синхронизирован блок {height}")

                except Exception as block_error:
                    logger.error(f"Ошибка синхронизации блока {height}: {block_error}")
                    errors += 1
                    continue

            # Обновляем статистику
            self._sync_stats["blocks_synced"] += synced_blocks
            self._sync_stats["transactions_synced"] += synced_transactions
            self._sync_stats["errors"] += errors
            self._sync_stats["last_sync_time"] = asyncio.get_event_loop().time()

            logger.info(
                f"Синхронизация завершена: блоков={synced_blocks}, "
                f"транзакций={synced_transactions}, ошибок={errors}"
            )

            return {
                "synced_blocks": synced_blocks,
                "synced_transactions": synced_transactions,
                "errors": errors,
                "message": f"Синхронизировано блоков: {synced_blocks}",
            }

        except Exception as e:
            logger.error(f"Ошибка синхронизации: {e}")
            raise SyncServiceError(f"Ошибка синхронизации: {e}")

        finally:
            self._is_syncing = False

    async def sync_mempool(self) -> Dict[str, Any]:
        """
        Синхронизация транзакций из мемпула

        Returns:
            Результат синхронизации мемпула
        """
        try:
            logger.info("Начинаем синхронизацию мемпула")

            # Получаем транзакции из мемпула
            mempool_transactions = self.transaction_service.get_mempool_transactions()
            synced_count = 0
            errors = 0

            for tx_data in mempool_transactions:
                try:
                    # Проверяем, есть ли уже эта транзакция в БД
                    existing_tx = self.transaction_service.get_transaction_by_txid(
                        tx_data["txid"]
                    )
                    if existing_tx:
                        continue

                    # Сохраняем транзакцию без привязки к блоку
                    tx_data_copy = tx_data.copy()
                    tx_data_copy.pop("blockhash", None)
                    tx_data_copy.pop("blockheight", None)

                    self.transaction_service.save_transaction_to_db(tx_data_copy)
                    synced_count += 1

                except Exception as tx_error:
                    logger.warning(
                        f"Ошибка синхронизации транзакции из мемпула "
                        f"{tx_data.get('txid')}: {tx_error}"
                    )
                    errors += 1

            logger.info(
                f"Синхронизация мемпула завершена: транзакций={synced_count}, "
                f"ошибок={errors}"
            )

            return {
                "synced_transactions": synced_count,
                "errors": errors,
                "message": f"Синхронизировано транзакций из мемпула: {synced_count}",
            }

        except Exception as e:
            logger.error(f"Ошибка синхронизации мемпула: {e}")
            raise SyncServiceError(f"Ошибка синхронизации мемпула: {e}")

    async def full_sync(self, batch_size: int = 100) -> Dict[str, Any]:
        """
        Полная синхронизация с блокчейном

        Args:
            batch_size: Размер батча для синхронизации

        Returns:
            Результат полной синхронизации
        """
        if self._is_syncing:
            raise SyncServiceError("Синхронизация уже выполняется")

        self._is_syncing = True
        total_synced_blocks = 0
        total_synced_transactions = 0
        total_errors = 0

        try:
            # Получаем информацию о текущем состоянии
            network_height = bitcoin_rpc.get_block_count()
            db_height = self.block_service.get_latest_block_height()

            logger.info(
                f"Начинаем полную синхронизацию: сеть={network_height}, БД={db_height}"
            )

            if db_height >= network_height:
                logger.info("База данных уже синхронизирована")
                return {
                    "synced_blocks": 0,
                    "synced_transactions": 0,
                    "errors": 0,
                    "message": "Уже синхронизировано",
                }

            # Синхронизируем батчами
            start_height = db_height + 1

            while start_height <= network_height:
                end_height = min(start_height + batch_size - 1, network_height)

                # Синхронизируем батч
                result = await self.sync_latest_blocks(
                    max_blocks=end_height - start_height + 1
                )

                total_synced_blocks += result["synced_blocks"]
                total_synced_transactions += result["synced_transactions"]
                total_errors += result["errors"]

                # Обновляем прогресс
                progress = (
                    (start_height + result["synced_blocks"]) / network_height * 100
                )
                self._sync_stats["sync_progress"] = round(progress, 2)

                logger.info(
                    f"Прогресс синхронизации: {progress:.1f}% "
                    f"({start_height + result['synced_blocks']}/{network_height})"
                )

                start_height = end_height + 1

                # Небольшая пауза между батчами
                await asyncio.sleep(0.1)

            logger.info(
                f"Полная синхронизация завершена: блоков={total_synced_blocks}, "
                f"транзакций={total_synced_transactions}, ошибок={total_errors}"
            )

            return {
                "synced_blocks": total_synced_blocks,
                "synced_transactions": total_synced_transactions,
                "errors": total_errors,
                "message": "Полная синхронизация завершена",
            }

        except Exception as e:
            logger.error(f"Ошибка полной синхронизации: {e}")
            raise SyncServiceError(f"Ошибка полной синхронизации: {e}")

        finally:
            self._is_syncing = False

    def handle_reorg(self, new_tip_hash: str) -> Dict[str, Any]:
        """
        Обработка реорганизации блокчейна

        Args:
            new_tip_hash: Хеш нового верхнего блока

        Returns:
            Результат обработки реорганизации
        """
        try:
            logger.warning(
                f"Обнаружена реорганизация блокчейна: новый tip {new_tip_hash}"
            )

            # Получаем информацию о новом верхнем блоке
            new_tip_data = bitcoin_rpc.get_block(new_tip_hash, verbosity=1)
            new_height = new_tip_data["height"]

            # Находим общий предок
            common_height = new_height
            while common_height > 0:
                block_hash = bitcoin_rpc.get_block_hash(common_height)
                db_block = self.block_service.get_block_by_height(common_height)

                if db_block and db_block.hash == block_hash:
                    # Нашли общий предок
                    break

                common_height -= 1

            logger.info(f"Общий предок найден на высоте {common_height}")

            # Удаляем блоки после общего предка
            orphaned_blocks = (
                self.db.query(Block).filter(Block.height > common_height).all()
            )

            orphaned_count = len(orphaned_blocks)
            for block in orphaned_blocks:
                # Удаляем связанные транзакции
                self.db.query(Transaction).filter(
                    Transaction.block_hash == block.hash
                ).delete()

                # Удаляем блок
                self.db.delete(block)

            self.db.commit()

            logger.info(f"Удалено {orphaned_count} орфанных блоков")

            return {
                "orphaned_blocks": orphaned_count,
                "common_ancestor_height": common_height,
                "message": f"Реорганизация обработана: удалено {orphaned_count} блоков",
            }

        except Exception as e:
            self.db.rollback()
            logger.error(f"Ошибка обработки реорганизации: {e}")
            raise SyncServiceError(f"Ошибка обработки реорганизации: {e}")

    async def check_for_reorg(self) -> bool:
        """
        Проверка на реорганизацию блокчейна

        Returns:
            True если обнаружена реорганизация
        """
        try:
            # Получаем последние несколько блоков из БД
            recent_blocks = (
                self.db.query(Block).order_by(Block.height.desc()).limit(10).all()
            )

            if not recent_blocks:
                return False

            # Проверяем каждый блок
            for block in recent_blocks:
                try:
                    # Получаем хеш блока на этой высоте из сети
                    network_hash = bitcoin_rpc.get_block_hash(block.height)

                    if network_hash != block.hash:
                        logger.warning(
                            f"Обнаружена реорганизация на высоте {block.height}: "
                            f"БД={block.hash}, сеть={network_hash}"
                        )
                        return True

                except BitcoinRPCError:
                    # Блок может быть временно недоступен
                    continue

            return False

        except Exception as e:
            logger.error(f"Ошибка проверки реорганизации: {e}")
            return False

    def validate_database_integrity(self) -> Dict[str, Any]:
        """
        Валидация целостности базы данных

        Returns:
            Результат валидации
        """
        try:
            logger.info("Начинаем валидацию целостности БД")

            issues = []
            checked_blocks = 0
            checked_transactions = 0

            # Проверяем блоки
            blocks = self.db.query(Block).order_by(Block.height).all()

            for i, block in enumerate(blocks):
                checked_blocks += 1

                # Проверяем последовательность высот
                if i > 0 and block.height != blocks[i - 1].height + 1:
                    issues.append(f"Пропущена высота блока: {blocks[i - 1].height + 1}")

                # Проверяем связи previous_block_hash
                if (
                    i > 0
                    and block.previous_block_hash
                    and block.previous_block_hash != blocks[i - 1].hash
                ):
                    issues.append(
                        f"Неверный previous_block_hash в блоке {block.height}"
                    )

                # Проверяем транзакции блока
                tx_count = (
                    self.db.query(Transaction)
                    .filter(Transaction.block_hash == block.hash)
                    .count()
                )

                if block.n_tx and tx_count != block.n_tx:
                    issues.append(
                        f"Несоответствие количества транзакций в блоке {block.height}: "
                        f"ожидается {block.n_tx}, найдено {tx_count}"
                    )

            # Проверяем транзакции
            orphaned_transactions = (
                self.db.query(Transaction)
                .filter(
                    Transaction.block_hash.isnot(None),
                    ~Transaction.block_hash.in_(self.db.query(Block.hash)),
                )
                .count()
            )

            if orphaned_transactions > 0:
                issues.append(f"Найдено {orphaned_transactions} орфанных транзакций")

            checked_transactions = self.db.query(Transaction).count()

            logger.info(
                f"Валидация завершена: проверено блоков={checked_blocks}, "
                f"транзакций={checked_transactions}, проблем={len(issues)}"
            )

            return {
                "is_valid": len(issues) == 0,
                "checked_blocks": checked_blocks,
                "checked_transactions": checked_transactions,
                "issues": issues,
                "message": (
                    "БД валидна"
                    if len(issues) == 0
                    else f"Найдено {len(issues)} проблем"
                ),
            }

        except Exception as e:
            logger.error(f"Ошибка валидации БД: {e}")
            raise SyncServiceError(f"Ошибка валидации БД: {e}")


def get_sync_service(db: Session = None) -> SyncService:
    """Получение экземпляра сервиса синхронизации"""
    if db is None:
        db = next(get_db())
    return SyncService(db)
