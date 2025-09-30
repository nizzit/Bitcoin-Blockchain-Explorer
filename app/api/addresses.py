"""
API endpoints для работы с адресами
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.address import Address, AddressTransactionList
from app.services.transaction_service import TransactionService

router = APIRouter(prefix="/addresses", tags=["addresses"])


@router.get("/{address}", response_model=Address)
async def get_address(
    address: str,
    db: Session = Depends(get_db),
):
    """
    Получить информацию об адресе
    """
    service = TransactionService(db)
    address_info = await service.get_address_info(address)

    if not address_info:
        raise HTTPException(status_code=404, detail=f"Адрес {address} не найден")

    return address_info


@router.get("/{address}/transactions")
async def get_address_transactions(
    address: str,
    page: int = Query(1, ge=1, description="Номер страницы"),
    limit: int = Query(25, ge=1, le=100, description="Количество транзакций"),
    db: Session = Depends(get_db),
):
    """
    Получить транзакции адреса
    """
    service = TransactionService(db)

    # Проверяем существование адреса
    address_info = await service.get_address_info(address)
    if not address_info:
        raise HTTPException(status_code=404, detail=f"Адрес {address} не найден")

    # Получаем транзакции
    transactions, total = await service.get_address_transactions(
        address=address,
        page=page,
        limit=limit,
    )

    return AddressTransactionList(
        address=address,
        transactions=transactions,
        total=total,
        page=page,
        limit=limit,
        pages=(total + limit - 1) // limit,
    )


@router.get("/{address}/utxos")
async def get_address_utxos(
    address: str,
    db: Session = Depends(get_db),
):
    """
    Получить UTXO адреса (неизрасходованные выходы транзакций)
    """
    service = TransactionService(db)

    # Проверяем существование адреса
    address_info = await service.get_address_info(address)
    if not address_info:
        raise HTTPException(status_code=404, detail=f"Адрес {address} не найден")

    # Получаем UTXO
    utxos = await service.get_address_utxos(address)

    return {
        "address": address,
        "utxos": utxos,
        "count": len(utxos),
        "total_value": sum(utxo.get("value", 0) for utxo in utxos),
    }
