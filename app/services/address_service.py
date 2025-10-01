"""
Сервис для работы с Bitcoin адресами
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import desc
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.address import Address
from app.models.transaction import TransactionInput, TransactionOutput

logger = logging.getLogger(__name__)


class AddressServiceError(Exception):
    """Исключение для ошибок сервиса адресов"""

    pass


class AddressService:
    """Сервис для работы с адресами"""

    def __init__(self, db: Session):
        self.db = db

    def get_address(self, address: str) -> Optional[Address]:
        """
        Получение адреса из БД

        Args:
            address: Bitcoin адрес
        """
        try:
            return self.db.query(Address).filter(Address.address == address).first()
        except Exception as e:
            logger.error(f"Ошибка получения адреса {address}: {e}")
            raise AddressServiceError(f"Не удалось получить адрес: {e}")

    def create_or_update_address(
        self, address: str, block_height: Optional[int] = None
    ) -> Address:
        """
        Создание или обновление адреса

        Args:
            address: Bitcoin адрес
            block_height: Высота блока (для отслеживания первого/последнего появления)
        """
        try:
            # Проверяем, существует ли адрес
            existing_address = self.get_address(address)

            if existing_address:
                # Обновляем существующий адрес
                if block_height:
                    if (
                        existing_address.first_seen_block is None
                        or block_height < existing_address.first_seen_block
                    ):
                        existing_address.first_seen_block = block_height

                    if (
                        existing_address.last_seen_block is None
                        or block_height > existing_address.last_seen_block
                    ):
                        existing_address.last_seen_block = block_height

                # Пересчитываем баланс и количество транзакций
                self._update_address_stats(existing_address)
                self.db.commit()
                self.db.refresh(existing_address)
                return existing_address
            else:
                # Создаем новый адрес
                new_address = Address(
                    address=address,
                    balance=0,
                    tx_count=0,
                    first_seen_block=block_height,
                    last_seen_block=block_height,
                )
                self.db.add(new_address)
                self.db.commit()
                self.db.refresh(new_address)

                # Обновляем статистику
                self._update_address_stats(new_address)
                self.db.commit()
                self.db.refresh(new_address)
                return new_address

        except IntegrityError as e:
            # Обрабатываем race condition
            self.db.rollback()
            logger.warning(f"Адрес {address} уже существует (race condition)")
            existing_address = self.get_address(address)
            if existing_address:
                return existing_address
            logger.error(f"Ошибка целостности БД для адреса {address}: {e}")
            raise AddressServiceError(f"Ошибка целостности БД: {e}")
        except Exception as e:
            self.db.rollback()
            logger.error(f"Ошибка создания/обновления адреса {address}: {e}")
            raise AddressServiceError(f"Не удалось создать/обновить адрес: {e}")

    def _update_address_stats(self, address: Address) -> None:
        """
        Обновление статистики адреса (баланс и количество транзакций)

        Args:
            address: Объект адреса для обновления
        """
        try:
            # Получаем все выходы для этого адреса
            outputs = (
                self.db.query(TransactionOutput)
                .filter(TransactionOutput.address == address.address)
                .all()
            )

            # Получаем потраченные выходы
            spent_outputs = set()
            for output in outputs:
                spent_input = (
                    self.db.query(TransactionInput)
                    .filter(
                        TransactionInput.prev_txid == output.transaction.txid,
                        TransactionInput.vout == output.n,
                    )
                    .first()
                )
                if spent_input:
                    spent_outputs.add((output.transaction.txid, output.n))

            # Вычисляем баланс
            total_received = sum(output.value for output in outputs)
            total_spent = sum(
                output.value
                for output in outputs
                if (output.transaction.txid, output.n) in spent_outputs
            )
            balance = total_received - total_spent

            # Подсчитываем уникальные транзакции
            unique_txids = set(output.transaction.txid for output in outputs)
            tx_count = len(unique_txids)

            # Обновляем адрес
            address.balance = balance
            address.tx_count = tx_count

        except Exception as e:
            logger.error(
                f"Ошибка обновления статистики для адреса {address.address}: {e}"
            )
            raise AddressServiceError(f"Не удалось обновить статистику адреса: {e}")

    def sync_address_from_outputs(
        self, address_str: str, block_height: Optional[int] = None
    ) -> Address:
        """
        Синхронизация адреса на основе выходов транзакций

        Args:
            address_str: Bitcoin адрес
            block_height: Высота блока
        """
        try:
            return self.create_or_update_address(address_str, block_height)
        except Exception as e:
            logger.error(f"Ошибка синхронизации адреса {address_str}: {e}")
            raise AddressServiceError(f"Не удалось синхронизировать адрес: {e}")

    def get_all_addresses_from_outputs(self) -> List[str]:
        """
        Получение всех уникальных адресов из выходов транзакций

        Returns:
            Список уникальных адресов
        """
        try:
            # Получаем все уникальные адреса из TransactionOutput
            addresses = (
                self.db.query(TransactionOutput.address)
                .filter(TransactionOutput.address.isnot(None))
                .distinct()
                .all()
            )
            return [addr[0] for addr in addresses]
        except Exception as e:
            logger.error(f"Ошибка получения адресов из выходов: {e}")
            raise AddressServiceError(f"Не удалось получить адреса из выходов: {e}")

    def sync_all_addresses(self) -> Dict[str, Any]:
        """
        Синхронизация всех адресов из TransactionOutput

        Returns:
            Статистика синхронизации
        """
        try:
            logger.info("Начинаем синхронизацию всех адресов")

            # Получаем все уникальные адреса
            unique_addresses = self.get_all_addresses_from_outputs()
            total_addresses = len(unique_addresses)
            synced_count = 0
            updated_count = 0
            errors = 0

            for address_str in unique_addresses:
                try:
                    # Получаем высоты блоков для этого адреса
                    first_output = (
                        self.db.query(TransactionOutput)
                        .join(TransactionOutput.transaction)
                        .filter(
                            TransactionOutput.address == address_str,
                            TransactionOutput.transaction.has(block_height__isnot=None),
                        )
                        .order_by(TransactionOutput.transaction.block_height)
                        .first()
                    )

                    block_height = (
                        first_output.transaction.block_height if first_output else None
                    )

                    # Проверяем, существует ли адрес
                    existing = self.get_address(address_str)

                    # Создаем или обновляем адрес
                    self.sync_address_from_outputs(address_str, block_height)

                    if existing:
                        updated_count += 1
                    else:
                        synced_count += 1

                except Exception as addr_error:
                    logger.warning(
                        f"Ошибка синхронизации адреса {address_str}: {addr_error}"
                    )
                    errors += 1

            logger.info(
                f"Синхронизация адресов завершена: новых={synced_count}, "
                f"обновлено={updated_count}, ошибок={errors}"
            )

            return {
                "total_unique_addresses": total_addresses,
                "synced_new": synced_count,
                "updated_existing": updated_count,
                "errors": errors,
                "message": f"Синхронизировано адресов: новых={synced_count}, обновлено={updated_count}",
            }

        except Exception as e:
            logger.error(f"Ошибка синхронизации всех адресов: {e}")
            raise AddressServiceError(f"Не удалось синхронизировать адреса: {e}")

    def get_addresses_paginated(
        self, page: int = 1, per_page: int = 50, sort_by: str = "balance"
    ) -> Dict[str, Any]:
        """
        Получение адресов с пагинацией

        Args:
            page: Номер страницы
            per_page: Количество адресов на странице
            sort_by: Поле для сортировки (balance, tx_count, created_at)
        """
        try:
            if page < 1:
                page = 1
            if per_page < 1 or per_page > 100:
                per_page = 50

            # Определяем поле для сортировки
            sort_field = Address.balance  # по умолчанию
            if sort_by == "tx_count":
                sort_field = Address.tx_count
            elif sort_by == "created_at":
                sort_field = Address.created_at

            query = self.db.query(Address).order_by(desc(sort_field))
            total = query.count()
            offset = (page - 1) * per_page
            addresses = query.offset(offset).limit(per_page).all()

            return {
                "addresses": addresses,
                "total": total,
                "page": page,
                "per_page": per_page,
                "total_pages": (total + per_page - 1) // per_page,
                "has_next": page * per_page < total,
                "has_prev": page > 1,
            }

        except Exception as e:
            logger.error(f"Ошибка пагинации адресов: {e}")
            raise AddressServiceError(f"Не удалось получить адреса: {e}")

    def get_richest_addresses(self, limit: int = 100) -> List[Address]:
        """
        Получение самых богатых адресов

        Args:
            limit: Количество адресов для возврата
        """
        try:
            return (
                self.db.query(Address)
                .filter(Address.balance > 0)
                .order_by(desc(Address.balance))
                .limit(limit)
                .all()
            )
        except Exception as e:
            logger.error(f"Ошибка получения богатых адресов: {e}")
            raise AddressServiceError(f"Не удалось получить богатые адреса: {e}")

    def get_total_addresses(self) -> int:
        """Получение общего количества адресов"""
        try:
            return self.db.query(Address).count()
        except Exception as e:
            logger.error(f"Ошибка получения количества адресов: {e}")
            return 0


def get_address_service(db: Session = None) -> AddressService:
    """Получение экземпляра сервиса адресов"""
    if db is None:
        db = next(get_db())
    return AddressService(db)
