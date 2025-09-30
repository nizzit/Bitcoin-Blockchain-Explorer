"""
API endpoints для работы с транзакциями
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.transaction import Transaction, TransactionList
from app.services.transaction_service import TransactionService

router = APIRouter(prefix="/transactions", tags=["transactions"])


@router.get("/latest", response_model=TransactionList)
async def get_latest_transactions(
    limit: int = Query(10, ge=1, le=50, description="Количество транзакций"),
    db: Session = Depends(get_db),
):
    """
    Получить последние подтвержденные транзакции
    """
    service = TransactionService(db)
    transactions, total = await service.get_latest_transactions(limit=limit)

    return TransactionList(
        transactions=transactions,
        total=total,
        page=1,
        limit=limit,
        pages=1,
    )


@router.get("/unconfirmed", response_model=TransactionList)
async def get_unconfirmed_transactions(
    page: int = Query(1, ge=1, description="Номер страницы"),
    limit: int = Query(10, ge=1, le=50, description="Количество транзакций"),
    db: Session = Depends(get_db),
):
    """
    Получить неподтвержденные транзакции из mempool
    """
    service = TransactionService(db)
    transactions, total = await service.get_unconfirmed_transactions(
        page=page, limit=limit
    )

    return TransactionList(
        transactions=transactions,
        total=total,
        page=page,
        limit=limit,
        pages=(total + limit - 1) // limit,
    )


@router.get("/{txid}", response_model=Transaction)
async def get_transaction(
    txid: str,
    db: Session = Depends(get_db),
):
    """
    Получить информацию о транзакции по txid
    """
    service = TransactionService(db)
    transaction = await service.get_transaction_by_txid(txid)

    if not transaction:
        raise HTTPException(status_code=404, detail=f"Транзакция {txid} не найдена")

    return transaction
