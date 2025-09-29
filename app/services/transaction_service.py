"""
Сервис для работы с транзакциями Bitcoin
"""

import logging
from typing import Any, Dict, List, Optional

from sqlalchemy import desc
from sqlalchemy.orm import Session

from app.database import get_db
from app.models.transaction import Transaction, TransactionInput, TransactionOutput
from app.services.bitcoin_rpc import BitcoinRPCError, bitcoin_rpc

logger = logging.getLogger(__name__)


class TransactionServiceError(Exception):
    """Исключение для ошибок сервиса транзакций"""

    pass


class TransactionService:
    """Сервис для работы с транзакциями"""

    def __init__(self, db: Session):
        self.db = db

    def get_transaction_by_txid(self, txid: str) -> Optional[Transaction]:
        """
        Получение транзакции по txid из БД

        Args:
            txid: ID транзакции
        """
        try:
            transaction = (
                self.db.query(Transaction).filter(Transaction.txid == txid).first()
            )
            return transaction
        except Exception as e:
            logger.error(f"Ошибка получения транзакции по txid {txid}: {e}")
            raise TransactionServiceError(f"Не удалось получить транзакцию: {e}")

    def get_latest_transactions(self, limit: int = 10) -> List[Transaction]:
        """
        Получение последних транзакций из БД

        Args:
            limit: Количество транзакций для возврата
        """
        try:
            transactions = (
                self.db.query(Transaction)
                .filter(Transaction.block_height.isnot(None))
                .order_by(desc(Transaction.block_height), desc(Transaction.id))
                .limit(limit)
                .all()
            )
            return transactions
        except Exception as e:
            logger.error(f"Ошибка получения последних транзакций: {e}")
            raise TransactionServiceError(
                f"Не удалось получить последние транзакции: {e}"
            )

    def get_unconfirmed_transactions(self, limit: int = 50) -> List[Transaction]:
        """
        Получение неподтвержденных транзакций (в мемпуле)

        Args:
            limit: Количество транзакций для возврата
        """
        try:
            transactions = (
                self.db.query(Transaction)
                .filter(Transaction.block_hash.is_(None))
                .order_by(desc(Transaction.id))
                .limit(limit)
                .all()
            )
            return transactions
        except Exception as e:
            logger.error(f"Ошибка получения неподтвержденных транзакций: {e}")
            raise TransactionServiceError(
                f"Не удалось получить неподтвержденные транзакции: {e}"
            )

    def get_transactions_paginated(
        self, page: int = 1, per_page: int = 50, confirmed_only: bool = True
    ) -> Dict[str, Any]:
        """
        Получение транзакций с пагинацией

        Args:
            page: Номер страницы (начиная с 1)
            per_page: Количество элементов на странице
            confirmed_only: Только подтвержденные транзакции
        """
        try:
            # Валидация параметров
            if page < 1:
                page = 1
            if per_page < 1 or per_page > 100:
                per_page = 50

            # Запрос с пагинацией
            query = self.db.query(Transaction)

            if confirmed_only:
                query = query.filter(Transaction.block_height.isnot(None))

            query = query.order_by(desc(Transaction.block_height), desc(Transaction.id))

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
            logger.error(f"Ошибка пагинации транзакций: {e}")
            raise TransactionServiceError(f"Не удалось получить транзакции: {e}")

    def fetch_transaction_from_rpc(self, txid: str) -> Dict[str, Any]:
        """
        Получение транзакции из Bitcoin Core через RPC

        Args:
            txid: ID транзакции
        """
        try:
            # Получаем транзакцию через RPC
            tx_data = bitcoin_rpc.get_raw_transaction(txid, verbose=True)
            return tx_data

        except BitcoinRPCError as e:
            logger.error(f"RPC ошибка при получении транзакции {txid}: {e}")
            raise TransactionServiceError(
                f"Не удалось получить транзакцию через RPC: {e}"
            )
        except Exception as e:
            logger.error(f"Неожиданная ошибка при получении транзакции {txid}: {e}")
            raise TransactionServiceError(f"Неожиданная ошибка: {e}")

    def save_transaction_to_db(self, tx_data: Dict[str, Any]) -> Transaction:
        """
        Сохранение транзакции в БД

        Args:
            tx_data: Данные транзакции из RPC
        """
        try:
            # Проверяем, существует ли транзакция
            existing_tx = self.get_transaction_by_txid(tx_data["txid"])
            if existing_tx:
                logger.info(f"Транзакция {tx_data['txid']} уже существует в БД")
                return existing_tx

            # Создаем новую транзакцию
            transaction = Transaction(
                txid=tx_data["txid"],
                block_hash=tx_data.get("blockhash"),
                block_height=tx_data.get("blockheight"),
                version=tx_data.get("version"),
                locktime=tx_data.get("locktime"),
                size=tx_data.get("size"),
                vsize=tx_data.get("vsize"),
                weight=tx_data.get("weight"),
                fee=self._calculate_fee(tx_data),
            )

            self.db.add(transaction)
            self.db.flush()  # Получаем ID транзакции

            # Сохраняем входы транзакции
            if "vin" in tx_data:
                for vin in tx_data["vin"]:
                    tx_input = TransactionInput(
                        transaction_id=transaction.id,
                        vout=vin.get("vout"),
                        prev_txid=vin.get("txid"),
                        script_sig=vin.get("scriptSig", {}).get("hex"),
                        sequence=vin.get("sequence"),
                    )
                    self.db.add(tx_input)

            # Сохраняем выходы транзакции
            if "vout" in tx_data:
                for vout in tx_data["vout"]:
                    # Извлекаем адрес из scriptPubKey
                    script_pubkey = vout.get("scriptPubKey", {})
                    addresses = script_pubkey.get("addresses", [])
                    address = addresses[0] if addresses else None

                    # Если нет поля addresses, пытаемся получить из address
                    if not address:
                        address = script_pubkey.get("address")

                    tx_output = TransactionOutput(
                        transaction_id=transaction.id,
                        n=vout.get("n"),
                        value=int(
                            vout.get("value", 0) * 100000000
                        ),  # Конвертируем BTC в сатоши
                        script_pubkey=script_pubkey.get("hex"),
                        address=address,
                    )
                    self.db.add(tx_output)

            self.db.commit()
            self.db.refresh(transaction)

            logger.info(f"Транзакция {transaction.txid} успешно сохранена в БД")
            return transaction

        except Exception as e:
            self.db.rollback()
            logger.error(f"Ошибка сохранения транзакции в БД: {e}")
            raise TransactionServiceError(f"Не удалось сохранить транзакцию: {e}")

    def _calculate_fee(self, tx_data: Dict[str, Any]) -> Optional[int]:
        """
        Вычисление комиссии транзакции

        Args:
            tx_data: Данные транзакции из RPC
        """
        try:
            # Если комиссия уже указана в данных
            if "fee" in tx_data:
                return int(abs(tx_data["fee"]) * 100000000)  # Конвертируем BTC в сатоши

            # Вычисляем комиссию как разность входов и выходов
            total_output = 0

            # Суммируем выходы
            for vout in tx_data.get("vout", []):
                total_output += int(vout.get("value", 0) * 100000000)

            # Для вычисления входов нужно получить предыдущие транзакции
            # Это может быть дорогой операцией, поэтому пропускаем для coinbase
            if tx_data.get("vin", [{}])[0].get("coinbase"):
                return 0  # Coinbase транзакция не имеет комиссии

            return None  # Не можем вычислить без дополнительных RPC запросов

        except Exception as e:
            logger.warning(f"Не удалось вычислить комиссию для транзакции: {e}")
            return None

    def get_or_fetch_transaction(self, txid: str) -> Transaction:
        """
        Получение транзакции из БД или через RPC

        Args:
            txid: ID транзакции
        """
        try:
            # Сначала пытаемся найти в БД
            transaction = self.get_transaction_by_txid(txid)
            if transaction:
                return transaction

            # Если не найдена в БД, получаем через RPC и сохраняем
            logger.info(f"Транзакция {txid} не найдена в БД, получаем через RPC")
            tx_data = self.fetch_transaction_from_rpc(txid)
            return self.save_transaction_to_db(tx_data)

        except Exception as e:
            logger.error(f"Ошибка получения транзакции {txid}: {e}")
            raise TransactionServiceError(f"Не удалось получить транзакцию: {e}")

    def get_transactions_by_address(
        self, address: str, page: int = 1, per_page: int = 50
    ) -> Dict[str, Any]:
        """
        Получение транзакций по адресу

        Args:
            address: Bitcoin адрес
            page: Номер страницы
            per_page: Количество транзакций на странице
        """
        try:
            # Валидация параметров
            if page < 1:
                page = 1
            if per_page < 1 or per_page > 100:
                per_page = 50

            # Получаем транзакции через выходы
            query = (
                self.db.query(Transaction)
                .join(TransactionOutput)
                .filter(TransactionOutput.address == address)
                .order_by(desc(Transaction.block_height), desc(Transaction.id))
                .distinct()
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
            logger.error(f"Ошибка получения транзакций для адреса {address}: {e}")
            raise TransactionServiceError(
                f"Не удалось получить транзакции для адреса: {e}"
            )

    def search_transactions(self, query: str) -> List[Transaction]:
        """
        Поиск транзакций по txid

        Args:
            query: Поисковый запрос (txid или его часть)
        """
        try:
            transactions = (
                self.db.query(Transaction)
                .filter(Transaction.txid.like(f"{query}%"))
                .limit(10)
                .all()
            )
            return transactions

        except Exception as e:
            logger.error(f"Ошибка поиска транзакций по запросу '{query}': {e}")
            raise TransactionServiceError(f"Ошибка поиска: {e}")

    def get_mempool_transactions(self) -> List[Dict[str, Any]]:
        """
        Получение транзакций из мемпула через RPC

        Returns:
            Список транзакций в мемпуле
        """
        try:
            mempool_txids = bitcoin_rpc.get_raw_mempool(verbose=False)
            transactions = []

            # Ограничиваем количество для производительности
            for txid in mempool_txids[:50]:
                try:
                    tx_data = bitcoin_rpc.get_raw_transaction(txid, verbose=True)
                    transactions.append(tx_data)
                except Exception as e:
                    logger.warning(
                        f"Не удалось получить транзакцию {txid} из мемпула: {e}"
                    )
                    continue

            return transactions

        except BitcoinRPCError as e:
            logger.error(f"Ошибка получения мемпула: {e}")
            raise TransactionServiceError(f"Не удалось получить мемпул: {e}")

    def get_transaction_count(self) -> int:
        """Получение общего количества транзакций в БД"""
        try:
            return self.db.query(Transaction).count()
        except Exception as e:
            logger.error(f"Ошибка получения количества транзакций: {e}")
            return 0

    def get_address_balance(self, address: str) -> Dict[str, Any]:
        """
        Вычисление баланса адреса на основе UTXO

        Args:
            address: Bitcoin адрес
        """
        try:
            # Получаем все выходы для адреса
            outputs = (
                self.db.query(TransactionOutput)
                .filter(TransactionOutput.address == address)
                .all()
            )

            # Получаем все входы, которые потратили эти выходы
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

            return {
                "address": address,
                "balance": balance,
                "total_received": total_received,
                "total_spent": total_spent,
                "tx_count": len(set(output.transaction.txid for output in outputs)),
            }

        except Exception as e:
            logger.error(f"Ошибка вычисления баланса для адреса {address}: {e}")
            raise TransactionServiceError(f"Не удалось вычислить баланс: {e}")


def get_transaction_service(db: Session = None) -> TransactionService:
    """Получение экземпляра сервиса транзакций"""
    if db is None:
        db = next(get_db())
    return TransactionService(db)
