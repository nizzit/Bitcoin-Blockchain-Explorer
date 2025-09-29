"""
SQLAlchemy модель для блоков Bitcoin
"""

from sqlalchemy import BigInteger, Column, DateTime, Float, Integer, String
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Block(Base):
    """Модель блока Bitcoin"""

    __tablename__ = "blocks"

    id = Column(Integer, primary_key=True, index=True)
    hash = Column(String(64), unique=True, nullable=False, index=True)
    height = Column(Integer, unique=True, nullable=False, index=True)
    version = Column(Integer)
    merkleroot = Column(String(64))
    time = Column(BigInteger, index=True)  # Unix timestamp
    nonce = Column(BigInteger)
    bits = Column(String(8))
    difficulty = Column(Float)
    chainwork = Column(String(64))
    n_tx = Column(Integer)  # Количество транзакций
    size = Column(Integer)  # Размер блока в байтах
    weight = Column(Integer)  # Вес блока
    previous_block_hash = Column(String(64), index=True)
    next_block_hash = Column(String(64), index=True)
    created_at = Column(DateTime, default=func.now())

    # Связь с транзакциями
    transactions = relationship("Transaction", back_populates="block")

    def __repr__(self):
        return f"<Block(height={self.height}, hash='{self.hash[:12]}...')>"
