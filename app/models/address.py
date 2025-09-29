"""
SQLAlchemy модель для Bitcoin адресов
"""

from sqlalchemy import BigInteger, Column, DateTime, Integer, String
from sqlalchemy.sql import func

from app.database import Base


class Address(Base):
    """Модель Bitcoin адреса"""

    __tablename__ = "addresses"

    id = Column(Integer, primary_key=True, index=True)
    address = Column(String(64), unique=True, nullable=False, index=True)
    balance = Column(BigInteger, default=0)  # Баланс в сатоши
    tx_count = Column(Integer, default=0)  # Количество транзакций
    first_seen_block = Column(Integer, index=True)  # Первое появление
    last_seen_block = Column(Integer, index=True)  # Последнее появление
    created_at = Column(DateTime, default=func.now())

    def __repr__(self):
        return f"<Address(address='{self.address}', balance={self.balance})>"
