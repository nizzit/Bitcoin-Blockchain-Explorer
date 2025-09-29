"""
SQLAlchemy модели для транзакций Bitcoin
"""

from sqlalchemy import BigInteger, Column, DateTime, ForeignKey, Integer, String, Text
from sqlalchemy.orm import relationship
from sqlalchemy.sql import func

from app.database import Base


class Transaction(Base):
    """Модель транзакции Bitcoin"""

    __tablename__ = "transactions"

    id = Column(Integer, primary_key=True, index=True)
    txid = Column(String(64), unique=True, nullable=False, index=True)
    block_hash = Column(String(64), ForeignKey("blocks.hash"), index=True)
    block_height = Column(Integer, index=True)
    version = Column(Integer)
    locktime = Column(BigInteger)
    size = Column(Integer)  # Размер транзакции в байтах
    vsize = Column(Integer)  # Виртуальный размер
    weight = Column(Integer)  # Вес транзакции
    fee = Column(BigInteger)  # Комиссия в сатоши
    created_at = Column(DateTime, default=func.now())

    # Связи
    block = relationship("Block", back_populates="transactions")
    inputs = relationship(
        "TransactionInput", back_populates="transaction", cascade="all, delete-orphan"
    )
    outputs = relationship(
        "TransactionOutput", back_populates="transaction", cascade="all, delete-orphan"
    )

    def __repr__(self):
        return f"<Transaction(txid='{self.txid[:12]}...', block_height={self.block_height})>"


class TransactionInput(Base):
    """Модель входа транзакции"""

    __tablename__ = "transaction_inputs"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    vout = Column(Integer)  # Индекс выхода в предыдущей транзакции
    prev_txid = Column(String(64), index=True)  # Hash предыдущей транзакции
    script_sig = Column(Text)  # Скрипт подписи
    sequence = Column(BigInteger)

    # Связь с транзакцией
    transaction = relationship("Transaction", back_populates="inputs")

    def __repr__(self):
        return f"<TransactionInput(prev_txid='{self.prev_txid[:12]}...', vout={self.vout})>"


class TransactionOutput(Base):
    """Модель выхода транзакции"""

    __tablename__ = "transaction_outputs"

    id = Column(Integer, primary_key=True, index=True)
    transaction_id = Column(Integer, ForeignKey("transactions.id"), nullable=False)
    n = Column(Integer)  # Индекс выхода в транзакции
    value = Column(BigInteger)  # Значение в сатоши
    script_pubkey = Column(Text)  # Скрипт публичного ключа
    address = Column(String(64), index=True)  # Bitcoin адрес

    # Связь с транзакцией
    transaction = relationship("Transaction", back_populates="outputs")

    def __repr__(self):
        return f"<TransactionOutput(address='{self.address}', value={self.value})>"
