"""
Pydantic схемы для Bitcoin адресов
"""

from datetime import datetime
from typing import TYPE_CHECKING, List, Optional

from pydantic import BaseModel, Field

if TYPE_CHECKING:
    from app.schemas.transaction import Transaction


class AddressBase(BaseModel):
    """Базовая схема адреса"""

    address: str = Field(..., description="Bitcoin адрес")
    balance: Optional[int] = Field(0, description="Баланс в сатоши")
    tx_count: Optional[int] = Field(0, description="Количество транзакций")
    first_seen_block: Optional[int] = Field(None, description="Первое появление")
    last_seen_block: Optional[int] = Field(None, description="Последнее появление")


class AddressCreate(AddressBase):
    """Схема для создания адреса"""

    pass


class AddressUpdate(BaseModel):
    """Схема для обновления адреса"""

    balance: Optional[int] = None
    tx_count: Optional[int] = None
    last_seen_block: Optional[int] = None


class Address(AddressBase):
    """Полная схема адреса"""

    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class AddressSummary(BaseModel):
    """Краткая информация об адресе"""

    address: str
    balance: Optional[int] = None
    tx_count: Optional[int] = None

    class Config:
        from_attributes = True


class AddressStats(BaseModel):
    """Статистика адреса"""

    address: str
    balance: int
    tx_count: int
    first_seen_block: Optional[int] = None
    last_seen_block: Optional[int] = None
    total_received: Optional[int] = Field(None, description="Всего получено сатоши")
    total_sent: Optional[int] = Field(None, description="Всего отправлено сатоши")

    class Config:
        from_attributes = True


class AddressTransactionList(BaseModel):
    """Список транзакций адреса с пагинацией"""

    address: str
    transactions: List["Transaction"]
    total: int
    page: int
    limit: int
    pages: int

    class Config:
        from_attributes = True


class AddressListResponse(BaseModel):
    """Ответ со списком адресов"""

    addresses: List[AddressSummary]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool
