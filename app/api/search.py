"""
API endpoints для поиска и статистики
"""

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.orm import Session

from app.database import get_db
from app.services.block_service import BlockService
from app.services.transaction_service import TransactionService

router = APIRouter(tags=["search"])


@router.get("/search")
async def search(
    q: str = Query(..., min_length=1, description="Поисковый запрос"),
    db: Session = Depends(get_db),
):
    """
    Универсальный поиск по блокам, транзакциям и адресам

    Поддерживаемые форматы:
    - Хеш блока (64 hex символа)
    - Высота блока (число)
    - Txid транзакции (64 hex символа)
    - Bitcoin адрес (начинается с 1, 3 или bc1)
    """
    block_service = BlockService(db)
    tx_service = TransactionService(db)

    results = {
        "query": q,
        "results": [],
    }

    # Проверяем, является ли запрос числом (высота блока)
    try:
        height = int(q)
        block = await block_service.get_block_by_height(height)
        if block:
            results["results"].append(
                {
                    "type": "block",
                    "data": block,
                }
            )
            return results
    except ValueError:
        pass

    # Проверяем, является ли запрос хешем (64 hex символа)
    if len(q) == 64 and all(c in "0123456789abcdefABCDEF" for c in q):
        # Может быть хеш блока
        block = await block_service.get_block_by_hash(q)
        if block:
            results["results"].append(
                {
                    "type": "block",
                    "data": block,
                }
            )
            return results

        # Или txid транзакции
        transaction = await tx_service.get_transaction_by_txid(q)
        if transaction:
            results["results"].append(
                {
                    "type": "transaction",
                    "data": transaction,
                }
            )
            return results

    # Проверяем, является ли запрос Bitcoin адресом
    if q.startswith(("1", "3", "bc1")) and len(q) >= 26:
        address_info = await tx_service.get_address_info(q)
        if address_info:
            results["results"].append(
                {
                    "type": "address",
                    "data": address_info,
                }
            )
            return results

    # Ничего не найдено
    raise HTTPException(
        status_code=404,
        detail=(
            f"По запросу '{q}' ничего не найдено. "
            "Поддерживаются: хеш блока, высота блока, txid транзакции, Bitcoin адрес."
        ),
    )


@router.get("/stats")
async def get_network_stats(
    db: Session = Depends(get_db),
):
    """
    Получить статистику сети
    """
    block_service = BlockService(db)
    tx_service = TransactionService(db)

    # Получаем последний блок
    latest_block = await block_service.get_latest_block()

    if not latest_block:
        raise HTTPException(
            status_code=503, detail="Статистика недоступна: блокчейн не синхронизирован"
        )

    # Подсчитываем статистику
    total_blocks = await block_service.get_total_blocks()
    total_transactions = await tx_service.get_total_transactions()

    # Получаем последние блоки для расчета средних значений
    recent_blocks, _ = await block_service.get_blocks(page=1, limit=100)

    avg_block_time = 0
    avg_block_size = 0
    if recent_blocks and len(recent_blocks) > 1:
        # Средний интервал между блоками (в секундах)
        time_diffs = []
        size_sum = 0
        for i in range(len(recent_blocks) - 1):
            time_diff = recent_blocks[i].time - recent_blocks[i + 1].time
            if time_diff > 0:
                time_diffs.append(time_diff)
            size_sum += recent_blocks[i].size or 0

        if time_diffs:
            avg_block_time = sum(time_diffs) / len(time_diffs)
        if recent_blocks:
            avg_block_size = size_sum / len(recent_blocks)

    return {
        "network": "Bitcoin",
        "latest_block": {
            "height": latest_block.height,
            "hash": latest_block.hash,
            "time": latest_block.time,
            "tx_count": latest_block.n_tx,
        },
        "statistics": {
            "total_blocks": total_blocks,
            "total_transactions": total_transactions,
            "avg_block_time_seconds": round(avg_block_time, 2),
            "avg_block_size_bytes": round(avg_block_size, 2),
            "difficulty": latest_block.difficulty,
        },
    }
