"""
API endpoints для работы с блоками
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.schemas.block import Block, BlockList
from app.services.block_service import BlockService

router = APIRouter(prefix="/blocks", tags=["blocks"])


@router.get("/latest", response_model=Block)
async def get_latest_block(db: Session = Depends(get_db)):
    """
    Получить последний блок
    """
    service = BlockService(db)
    block = await service.get_latest_block()
    if not block:
        raise HTTPException(status_code=404, detail="Блок не найден")
    return block


@router.get("", response_model=BlockList)
async def get_blocks(
    page: int = Query(1, ge=1, description="Номер страницы"),
    limit: int = Query(10, ge=1, le=100, description="Количество блоков на странице"),
    db: Session = Depends(get_db),
):
    """
    Получить список последних блоков с пагинацией
    """
    service = BlockService(db)
    blocks, total = await service.get_blocks(page=page, limit=limit)

    return BlockList(
        blocks=blocks,
        total=total,
        page=page,
        limit=limit,
        pages=(total + limit - 1) // limit,
    )


@router.get("/{hash_or_height}", response_model=Block)
async def get_block(
    hash_or_height: str,
    db: Session = Depends(get_db),
):
    """
    Получить информацию о блоке по хешу или высоте
    """
    service = BlockService(db)

    # Проверяем, является ли параметр числом (высотой) или хешем
    try:
        height = int(hash_or_height)
        block = await service.get_block_by_height(height)
    except ValueError:
        # Это хеш блока
        block = await service.get_block_by_hash(hash_or_height)

    if not block:
        raise HTTPException(status_code=404, detail=f"Блок {hash_or_height} не найден")

    return block


@router.get("/{block_hash}/transactions")
async def get_block_transactions(
    block_hash: str,
    page: int = Query(1, ge=1, description="Номер страницы"),
    limit: int = Query(
        25, ge=1, le=100, description="Количество транзакций на странице"
    ),
    db: Session = Depends(get_db),
):
    """
    Получить транзакции блока
    """
    service = BlockService(db)

    # Проверяем существование блока
    block = await service.get_block_by_hash(block_hash)
    if not block:
        raise HTTPException(status_code=404, detail=f"Блок {block_hash} не найден")

    # Получаем транзакции
    transactions, total = await service.get_block_transactions(
        block_hash=block_hash,
        page=page,
        limit=limit,
    )

    return {
        "block_hash": block_hash,
        "transactions": transactions,
        "total": total,
        "page": page,
        "limit": limit,
        "pages": (total + limit - 1) // limit,
    }
