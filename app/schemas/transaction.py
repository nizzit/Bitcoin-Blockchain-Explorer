"""
Pydantic схемы для транзакций Bitcoin
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class TransactionInputBase(BaseModel):
    """Базовая схема входа транзакции"""

    vout: Optional[int] = Field(
        None, description="Индекс выхода в предыдущей транзакции"
    )
    prev_txid: Optional[str] = Field(None, description="Hash предыдущей транзакции")
    script_sig: Optional[str] = Field(None, description="Скрипт подписи")
    sequence: Optional[int] = Field(None, description="Sequence number")


class TransactionInputCreate(TransactionInputBase):
    """Схема для создания входа транзакции"""

    pass


class TransactionInput(TransactionInputBase):
    """Полная схема входа транзакции"""

    id: int
    transaction_id: int

    class Config:
        from_attributes = True


class TransactionOutputBase(BaseModel):
    """Базовая схема выхода транзакции"""

    n: Optional[int] = Field(None, description="Индекс выхода в транзакции")
    value: Optional[int] = Field(None, description="Значение в сатоши")
    script_pubkey: Optional[str] = Field(None, description="Скрипт публичного ключа")
    address: Optional[str] = Field(None, description="Bitcoin адрес")


class TransactionOutputCreate(TransactionOutputBase):
    """Схема для создания выхода транзакции"""

    pass


class TransactionOutput(TransactionOutputBase):
    """Полная схема выхода транзакции"""

    id: int
    transaction_id: int

    class Config:
        from_attributes = True


class TransactionBase(BaseModel):
    """Базовая схема транзакции"""

    txid: str = Field(..., description="ID транзакции")
    block_hash: Optional[str] = Field(None, description="Hash блока")
    block_height: Optional[int] = Field(None, description="Высота блока")
    version: Optional[int] = Field(None, description="Версия транзакции")
    locktime: Optional[int] = Field(None, description="Locktime")
    size: Optional[int] = Field(None, description="Размер транзакции в байтах")
    vsize: Optional[int] = Field(None, description="Виртуальный размер")
    weight: Optional[int] = Field(None, description="Вес транзакции")
    fee: Optional[int] = Field(None, description="Комиссия в сатоши")


class TransactionCreate(TransactionBase):
    """Схема для создания транзакции"""

    inputs: List[TransactionInputCreate] = []
    outputs: List[TransactionOutputCreate] = []


class Transaction(TransactionBase):
    """Полная схема транзакции"""

    id: int
    created_at: datetime
    inputs: List[TransactionInput] = []
    outputs: List[TransactionOutput] = []

    class Config:
        from_attributes = True


class TransactionSummary(BaseModel):
    """Краткая информация о транзакции"""

    txid: str
    block_height: Optional[int] = None
    size: Optional[int] = None
    fee: Optional[int] = None

    class Config:
        from_attributes = True


class TransactionList(BaseModel):
    """Список транзакций с пагинацией"""

    transactions: List[Transaction]
    total: int
    page: int
    limit: int
    pages: int

    class Config:
        from_attributes = True


class TransactionListResponse(BaseModel):
    """Ответ со списком транзакций"""

    transactions: List[TransactionSummary]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool
