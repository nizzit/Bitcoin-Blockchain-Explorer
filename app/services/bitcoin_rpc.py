"""
Bitcoin RPC клиент для взаимодействия с Bitcoin Core
"""

import logging
from typing import Any, Dict, List, Optional

from bitcoinrpc.authproxy import AuthServiceProxy, JSONRPCException

from app.config import settings

logger = logging.getLogger(__name__)


class BitcoinRPCError(Exception):
    """Исключение для ошибок Bitcoin RPC"""

    pass


class BitcoinRPCClient:
    """
    Клиент для взаимодействия с Bitcoin Core через RPC
    """

    def __init__(self):
        self._connection = None
        self._connect()

    def _connect(self) -> None:
        """Создание подключения к Bitcoin Core"""
        try:
            rpc_url = (
                f"http://{settings.BITCOIN_RPC_USER}:{settings.BITCOIN_RPC_PASSWORD}"
                f"@{settings.BITCOIN_RPC_HOST}:{settings.BITCOIN_RPC_PORT}/"
            )
            self._connection = AuthServiceProxy(
                rpc_url, timeout=settings.BITCOIN_RPC_TIMEOUT
            )
            # Проверяем подключение
            self._connection.getblockchaininfo()
            logger.info("Успешно подключено к Bitcoin Core")
        except Exception as e:
            logger.error(f"Ошибка подключения к Bitcoin Core: {e}")
            raise BitcoinRPCError(f"Не удалось подключиться к Bitcoin Core: {e}")

    def _reconnect(self) -> None:
        """Переподключение к Bitcoin Core"""
        logger.info("Попытка переподключения к Bitcoin Core...")
        self._connect()

    def _execute_rpc_call(self, method: str, *args) -> Any:
        """
        Выполнение RPC вызова с обработкой ошибок и переподключением
        """
        max_retries = 3
        retry_count = 0

        while retry_count < max_retries:
            try:
                if not self._connection:
                    self._connect()

                result = getattr(self._connection, method)(*args)
                return result

            except JSONRPCException as e:
                logger.error(f"JSON RPC ошибка в {method}: {e}")
                raise BitcoinRPCError(f"RPC ошибка: {e}")

            except Exception as e:
                retry_count += 1
                logger.warning(
                    f"Ошибка соединения в {method} "
                    f"(попытка {retry_count}/{max_retries}): {e}"
                )

                if retry_count < max_retries:
                    try:
                        self._reconnect()
                    except Exception as reconnect_error:
                        logger.error(f"Ошибка переподключения: {reconnect_error}")
                        if retry_count == max_retries - 1:
                            raise BitcoinRPCError(
                                f"Не удалось переподключиться: {reconnect_error}"
                            )
                else:
                    raise BitcoinRPCError(
                        f"Максимальное количество попыток исчерпано: {e}"
                    )

    # Методы для работы с блокчейном

    def get_blockchain_info(self) -> Dict[str, Any]:
        """Получение общей информации о блокчейне"""
        return self._execute_rpc_call("getblockchaininfo")

    def get_best_block_hash(self) -> str:
        """Получение хеша последнего блока"""
        return self._execute_rpc_call("getbestblockhash")

    def get_block_count(self) -> int:
        """Получение количества блоков в цепи"""
        return self._execute_rpc_call("getblockcount")

    def get_block_hash(self, height: int) -> str:
        """Получение хеша блока по высоте"""
        return self._execute_rpc_call("getblockhash", height)

    # Методы для работы с блоками

    def get_block(self, block_hash: str, verbosity: int = 2) -> Dict[str, Any]:
        """
        Получение информации о блоке

        Args:
            block_hash: Хеш блока
            verbosity: Уровень детализации (0=hex, 1=json, 2=json+transactions)
        """
        return self._execute_rpc_call("getblock", block_hash, verbosity)

    def get_block_header(self, block_hash: str, verbose: bool = True) -> Dict[str, Any]:
        """Получение заголовка блока"""
        return self._execute_rpc_call("getblockheader", block_hash, verbose)

    def get_block_stats(self, hash_or_height: str | int) -> Dict[str, Any]:
        """Получение статистики блока"""
        try:
            return self._execute_rpc_call("getblockstats", hash_or_height)
        except BitcoinRPCError:
            # Если getblockstats недоступен, возвращаем пустую статистику
            return {}

    # Методы для работы с транзакциями

    def get_raw_transaction(
        self, txid: str, verbose: bool = True, block_hash: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Получение информации о транзакции

        Args:
            txid: ID транзакции
            verbose: Возвращать JSON вместо hex
            block_hash: Хеш блока (для ускорения поиска)
        """
        if block_hash:
            return self._execute_rpc_call(
                "getrawtransaction", txid, verbose, block_hash
            )
        else:
            return self._execute_rpc_call("getrawtransaction", txid, verbose)

    def get_transaction(self, txid: str) -> Dict[str, Any]:
        """Получение информации о транзакции (из кошелька)"""
        try:
            return self._execute_rpc_call("gettransaction", txid)
        except BitcoinRPCError:
            # Если транзакция не в кошельке, используем getrawtransaction
            return self.get_raw_transaction(txid)

    def decode_raw_transaction(self, hex_string: str) -> Dict[str, Any]:
        """Декодирование сырой транзакции из hex"""
        return self._execute_rpc_call("decoderawtransaction", hex_string)

    # Методы для работы с мемпулом

    def get_mempool_info(self) -> Dict[str, Any]:
        """Получение информации о мемпуле"""
        return self._execute_rpc_call("getmempoolinfo")

    def get_raw_mempool(self, verbose: bool = False) -> List[str] | Dict[str, Any]:
        """Получение списка транзакций в мемпуле"""
        return self._execute_rpc_call("getrawmempool", verbose)

    def get_mempool_entry(self, txid: str) -> Dict[str, Any]:
        """Получение информации о транзакции в мемпуле"""
        return self._execute_rpc_call("getmempoolentry", txid)

    # Методы для работы с сетью

    def get_network_info(self) -> Dict[str, Any]:
        """Получение информации о сети"""
        return self._execute_rpc_call("getnetworkinfo")

    def get_peer_info(self) -> List[Dict[str, Any]]:
        """Получение информации о пирах"""
        return self._execute_rpc_call("getpeerinfo")

    def get_connection_count(self) -> int:
        """Получение количества соединений"""
        return self._execute_rpc_call("getconnectioncount")

    # Методы для работы с адресами и UTXO

    def validate_address(self, address: str) -> Dict[str, Any]:
        """Валидация Bitcoin адреса"""
        return self._execute_rpc_call("validateaddress", address)

    def get_address_info(self, address: str) -> Dict[str, Any]:
        """Получение информации об адресе"""
        try:
            return self._execute_rpc_call("getaddressinfo", address)
        except BitcoinRPCError:
            # Если getaddressinfo недоступен, используем validateaddress
            return self.validate_address(address)

    def list_unspent(
        self,
        min_conf: int = 1,
        max_conf: int = 9999999,
        addresses: Optional[List[str]] = None,
    ) -> List[Dict[str, Any]]:
        """Получение списка неизрасходованных выходов"""
        if addresses:
            return self._execute_rpc_call("listunspent", min_conf, max_conf, addresses)
        else:
            return self._execute_rpc_call("listunspent", min_conf, max_conf)

    # Методы для поиска

    def search_raw_transactions(
        self, address: str, verbose: bool = True, skip: int = 0, count: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Поиск транзакций по адресу (если доступно)
        Требует txindex=1 в bitcoin.conf
        """
        try:
            return self._execute_rpc_call(
                "searchrawtransactions", address, verbose, skip, count
            )
        except BitcoinRPCError:
            # Если метод недоступен, возвращаем пустой список
            logger.warning("searchrawtransactions недоступен, требуется txindex=1")
            return []

    # Утилиты

    def get_difficulty(self) -> float:
        """Получение текущей сложности"""
        return self._execute_rpc_call("getdifficulty")

    def get_mining_info(self) -> Dict[str, Any]:
        """Получение информации о майнинге"""
        return self._execute_rpc_call("getmininginfo")

    def estimate_smart_fee(self, conf_target: int = 6) -> Dict[str, Any]:
        """Оценка комиссии для подтверждения в заданное количество блоков"""
        return self._execute_rpc_call("estimatesmartfee", conf_target)

    async def test_connection(self) -> bool:
        """Тестирование подключения к Bitcoin Core"""
        try:
            self.get_blockchain_info()
            return True
        except Exception as e:
            logger.error(f"Тест подключения неудачен: {e}")
            return False

    def close(self) -> None:
        """Закрытие соединения"""
        if self._connection:
            self._connection = None
            logger.info("Соединение с Bitcoin Core закрыто")


# Глобальный экземпляр клиента
bitcoin_rpc = BitcoinRPCClient()
