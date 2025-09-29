"""
Pydantic схемы для блоков Bitcoin
"""

from datetime import datetime
from typing import List, Optional

from pydantic import BaseModel, Field


class BlockBase(BaseModel):
    """Базовая схема блока"""

    hash: str = Field(..., description="Hash блока")
    height: int = Field(..., description="Высота блока")
    version: Optional[int] = Field(None, description="Версия блока")
    merkleroot: Optional[str] = Field(None, description="Merkle root")
    time: Optional[int] = Field(None, description="Время блока (Unix timestamp)")
    nonce: Optional[int] = Field(None, description="Nonce")
    bits: Optional[str] = Field(None, description="Bits")
    difficulty: Optional[float] = Field(None, description="Сложность")
    chainwork: Optional[str] = Field(None, description="Chainwork")
    n_tx: Optional[int] = Field(None, description="Количество транзакций")
    size: Optional[int] = Field(None, description="Размер блока в байтах")
    weight: Optional[int] = Field(None, description="Вес блока")
    previous_block_hash: Optional[str] = Field(
        None, description="Hash предыдущего блока"
    )
    next_block_hash: Optional[str] = Field(None, description="Hash следующего блока")


class BlockCreate(BlockBase):
    """Схема для создания блока"""

    pass


class BlockUpdate(BaseModel):
    """Схема для обновления блока"""

    next_block_hash: Optional[str] = None


class Block(BlockBase):
    """Полная схема блока"""

    id: int
    created_at: datetime

    class Config:
        from_attributes = True


class BlockSummary(BaseModel):
    """Краткая информация о блоке"""

    hash: str
    height: int
    time: Optional[int] = None
    n_tx: Optional[int] = None
    size: Optional[int] = None

    class Config:
        from_attributes = True


class BlockWithTransactions(Block):
    """Блок с транзакциями"""

    from app.schemas.transaction import TransactionSummary

    transactions: List[TransactionSummary] = []

    class Config:
        from_attributes = True


class BlockListResponse(BaseModel):
    """Ответ со списком блоков"""

    blocks: List[BlockSummary]
    total: int
    page: int
    per_page: int
    has_next: bool
    has_prev: bool
