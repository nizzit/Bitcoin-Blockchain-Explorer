"""
Сервис для работы с блоками Bitcoin
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import asc, desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.block import Block
from app.models.transaction import Transaction
from app.services.bitcoin_rpc import BitcoinRPCError, bitcoin_rpc

logger = logging.getLogger(__name__)


class BlockServiceError(Exception):
    """Исключение для ошибок сервиса блоков"""

    pass


class BlockService:
    """Сервис для работы с блоками"""

    def __init__(self, db: Session):
        self.db = db

    async def get_latest_block(self) -> Optional[Block]:
        """
        Получение последнего блока из БД
        """
        try:
            block = self.db.query(Block).order_by(desc(Block.height)).first()
            return block
        except Exception as e:
            logger.error(f"Ошибка получения последнего блока: {e}")
            raise BlockServiceError(f"Не удалось получить последний блок: {e}")

    def get_latest_blocks(self, limit: int = 10, offset: int = 0) -> List[Block]:
        """
        Получение последних блоков из БД

        Args:
            limit: Количество блоков для возврата
            offset: Смещение для пагинации
        """
        try:
            blocks = (
                self.db.query(Block)
                .order_by(desc(Block.height))
                .offset(offset)
                .limit(limit)
                .all()
            )
            return blocks
        except Exception as e:
            logger.error(f"Ошибка получения последних блоков: {e}")
            raise BlockServiceError(f"Не удалось получить последние блоки: {e}")

    async def get_blocks(self, page: int = 1, limit: int = 10):
        """
        Получение блоков с пагинацией (упрощенная версия)

        Args:
            page: Номер страницы
            limit: Количество блоков
        """
        try:
            query = self.db.query(Block).order_by(desc(Block.height))
            total = query.count()
            offset = (page - 1) * limit
            blocks = query.offset(offset).limit(limit).all()
            return blocks, total
        except Exception as e:
            logger.error(f"Ошибка получения блоков: {e}")
            raise BlockServiceError(f"Не удалось получить блоки: {e}")

    async def get_total_blocks(self) -> int:
        """Получение общего количества блоков в БД"""
        try:
            return self.db.query(Block).count()
        except Exception as e:
            logger.error(f"Ошибка подсчета блоков: {e}")
            return 0

    async def get_block_by_hash(self, block_hash: str) -> Optional[Block]:
        """
        Получение блока по хешу из БД

        Args:
            block_hash: Хеш блока
        """
        try:
            block = self.db.query(Block).filter(Block.hash == block_hash).first()
            return block
        except Exception as e:
            logger.error(f"Ошибка получения блока по хешу {block_hash}: {e}")
            raise BlockServiceError(f"Не удалось получить блок: {e}")

    async def get_block_by_height(self, height: int) -> Optional[Block]:
        """
        Получение блока по высоте из БД

        Args:
            height: Высота блока
        """
        try:
            block = self.db.query(Block).filter(Block.height == height).first()
            return block
        except Exception as e:
            logger.error(f"Ошибка получения блока по высоте {height}: {e}")
            raise BlockServiceError(f"Не удалось получить блок: {e}")

    def get_blocks_paginated(
        self, page: int = 1, per_page: int = 20, order: str = "desc"
    ) -> Dict[str, Any]:
        """
        Получение блоков с пагинацией

        Args:
            page: Номер страницы (начиная с 1)
            per_page: Количество элементов на странице
            order: Порядок сортировки ('asc' или 'desc')
        """
        try:
            # Валидация параметров
            if page < 1:
                page = 1
            if per_page < 1 or per_page > 100:
                per_page = 20

            # Запрос с пагинацией
            query = self.db.query(Block)

            if order == "asc":
                query = query.order_by(asc(Block.height))
            else:
                query = query.order_by(desc(Block.height))

            total = query.count()
            offset = (page - 1) * per_page
            blocks = query.offset(offset).limit(per_page).all()

            return {
                "blocks": blocks,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": (total + per_page - 1) // per_page,
                "has_next": page * per_page < total,
                "has_prev": page > 1,
            }
        except Exception as e:
            logger.error(f"Ошибка пагинации блоков: {e}")
            raise BlockServiceError(f"Не удалось получить блоки: {e}")

    def fetch_block_from_rpc(self, hash_or_height: str | int) -> Dict[str, Any]:
        """
        Получение блока из Bitcoin Core через RPC

        Args:
            hash_or_height: Хеш блока или высота
        """
        try:
            # Если передан int или строка с числом, получаем хеш по высоте
            if isinstance(hash_or_height, int) or hash_or_height.isdigit():
                height = int(hash_or_height)

                # Проверяем, что высота не превышает текущую высоту сети
                network_height = bitcoin_rpc.get_block_count()
                if height > network_height:
                    raise BlockServiceError(
                        f"Запрошенная высота {height} превышает текущую "
                        f"высоту сети {network_height}"
                    )

                block_hash = bitcoin_rpc.get_block_hash(height)
            else:
                block_hash = hash_or_height

            # Получаем полную информацию о блоке
            block_data = bitcoin_rpc.get_block(block_hash, verbosity=2)

            # Получаем дополнительную статистику если доступна
            stats = bitcoin_rpc.get_block_stats(block_hash)
            if stats:
                block_data.update(stats)

            return block_data

        except BitcoinRPCError as e:
            logger.error(f"RPC ошибка при получении блока {hash_or_height}: {e}")
            raise BlockServiceError(f"Не удалось получить блок через RPC: {e}")
        except Exception as e:
            logger.error(
                f"Неожиданная ошибка при получении блока {hash_or_height}: {e}"
            )
            raise BlockServiceError(f"Неожиданная ошибка: {e}")

    async def save_block_to_db(self, block_data: Dict[str, Any]) -> Block:
        """
        Сохранение блока в БД

        Args:
            block_data: Данные блока из RPC
        """
        try:
            # Проверяем, существует ли блок
            existing_block = await self.get_block_by_hash(block_data["hash"])
            if existing_block:
                logger.info(f"Блок {block_data['hash']} уже существует в БД")
                return existing_block

            # Создаем новый блок
            block = Block(
                hash=block_data["hash"],
                height=block_data["height"],
                version=block_data.get("version"),
                merkleroot=block_data.get("merkleroot"),
                time=block_data.get("time"),  # Сохраняем как Unix timestamp (int)
                nonce=block_data.get("nonce"),
                bits=block_data.get("bits"),
                difficulty=block_data.get("difficulty"),
                chainwork=block_data.get("chainwork"),
                n_tx=block_data.get("nTx", len(block_data.get("tx", []))),
                size=block_data.get("size"),
                weight=block_data.get("weight"),
                previous_block_hash=block_data.get("previousblockhash"),
                next_block_hash=block_data.get("nextblockhash"),
            )

            self.db.add(block)
            self.db.commit()
            self.db.refresh(block)

            logger.info(f"Блок {block.hash} успешно сохранен в БД")
            return block

        except Exception as e:
            self.db.rollback()
            logger.error(f"Ошибка сохранения блока в БД: {e}")
            raise BlockServiceError(f"Не удалось сохранить блок: {e}")

    async def get_or_fetch_block(self, hash_or_height: str | int) -> Block:
        """
        Получение блока из БД или через RPC

        Args:
            hash_or_height: Хеш блока или высота
        """
        try:
            # Сначала пытаемся найти в БД
            if isinstance(hash_or_height, int) or hash_or_height.isdigit():
                block = await self.get_block_by_height(int(hash_or_height))
            else:
                block = await self.get_block_by_hash(hash_or_height)

            if block:
                return block

            # Если не найден в БД, получаем через RPC и сохраняем
            logger.info(f"Блок {hash_or_height} не найден в БД, получаем через RPC")
            block_data = self.fetch_block_from_rpc(hash_or_height)
            return await self.save_block_to_db(block_data)

        except Exception as e:
            logger.error(f"Ошибка получения блока {hash_or_height}: {e}")
            raise BlockServiceError(f"Не удалось получить блок: {e}")

    async def get_block_transactions(
        self, block_hash: str, page: int = 1, limit: int = 25
    ):
        """
        Получение транзакций блока с пагинацией

        Args:
            block_hash: Хеш блока
            page: Номер страницы
            limit: Количество транзакций на странице
        """
        try:
            query = (
                self.db.query(Transaction)
                .filter(Transaction.block_hash == block_hash)
                .order_by(Transaction.id)
            )
            total = query.count()
            offset = (page - 1) * limit
            transactions = query.offset(offset).limit(limit).all()
            return transactions, total
        except Exception as e:
            logger.error(f"Ошибка получения транзакций блока {block_hash}: {e}")
            raise BlockServiceError(f"Не удалось получить транзакции блока: {e}")

    def get_block_transactions_paginated(
        self, block_hash: str, page: int = 1, per_page: int = 50
    ) -> Dict[str, Any]:
        """
        Получение транзакций блока с пагинацией (старая версия)

        Args:
            block_hash: Хеш блока
            page: Номер страницы
            per_page: Количество транзакций на странице
        """
        try:
            # Валидация параметров
            if page < 1:
                page = 1
            if per_page < 1 or per_page > 100:
                per_page = 50

            # Получаем транзакции блока
            query = (
                self.db.query(Transaction)
                .filter(Transaction.block_hash == block_hash)
                .order_by(Transaction.id)
            )

            total = query.count()
            offset = (page - 1) * per_page
            transactions = query.offset(offset).limit(per_page).all()

            return {
                "transactions": transactions,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": (total + per_page - 1) // per_page,
                "has_next": page * per_page < total,
                "has_prev": page > 1,
            }

        except Exception as e:
            logger.error(f"Ошибка получения транзакций блока {block_hash}: {e}")
            raise BlockServiceError(f"Не удалось получить транзакции блока: {e}")

    def get_latest_block_height(self) -> int:
        """Получение высоты последнего блока в БД"""
        try:
            latest_block = self.db.query(Block).order_by(desc(Block.height)).first()
            return latest_block.height if latest_block else 0
        except Exception as e:
            logger.error(f"Ошибка получения высоты последнего блока: {e}")
            return 0

    def get_block_count_from_rpc(self) -> int:
        """Получение количества блоков из Bitcoin Core"""
        try:
            return bitcoin_rpc.get_block_count()
        except BitcoinRPCError as e:
            logger.error(f"Ошибка получения количества блоков из RPC: {e}")
            raise BlockServiceError(f"Не удалось получить количество блоков: {e}")

    def get_blockchain_info(self) -> Dict[str, Any]:
        """Получение общей информации о блокчейне"""
        try:
            info = bitcoin_rpc.get_blockchain_info()

            # Добавляем информацию из БД
            latest_db_height = self.get_latest_block_height()
            info["db_height"] = latest_db_height
            info["sync_progress"] = (
                latest_db_height / info["blocks"] * 100
                if info.get("blocks", 0) > 0
                else 0
            )

            return info
        except BitcoinRPCError as e:
            logger.error(f"Ошибка получения информации о блокчейне: {e}")
            raise BlockServiceError(f"Не удалось получить информацию о блокчейне: {e}")

    async def search_blocks(self, query: str) -> List[Block]:
        """
        Поиск блоков по хешу или высоте

        Args:
            query: Поисковый запрос (хеш или высота)
        """
        try:
            blocks = []

            # Поиск по высоте
            if query.isdigit():
                height = int(query)
                block = await self.get_block_by_height(height)
                if block:
                    blocks.append(block)

            # Поиск по хешу (частичное совпадение)
            else:
                blocks = (
                    self.db.query(Block)
                    .filter(Block.hash.like(f"{query}%"))
                    .limit(10)
                    .all()
                )

            return blocks

        except Exception as e:
            logger.error(f"Ошибка поиска блоков по запросу '{query}': {e}")
            raise BlockServiceError(f"Ошибка поиска: {e}")


def get_block_service(db: Session = None) -> BlockService:
    """Получение экземпляра сервиса блоков"""
    if db is None:
        db = next(get_db())
    return BlockService(db)
