"""
Главное FastAPI приложение Bitcoin Blockchain Explorer
"""

from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api import addresses, blocks, cache, search, sync, transactions
from app.background import lifespan
from app.config import settings
from app.database import get_db
from app.models.address import Address
from app.services.block_service import BlockService
from app.services.transaction_service import TransactionService

# Создаем FastAPI приложение
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Минималистичный blockchain explorer для Bitcoin",
    docs_url="/docs",
    redoc_url="/redoc",
    debug=True,
    lifespan=lifespan,
)

# Настройка CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=settings.BACKEND_CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Подключение статических файлов
app.mount("/static", StaticFiles(directory="app/static"), name="static")

# Настройка шаблонов Jinja2
templates = Jinja2Templates(directory="app/templates")

# Подключение API роутеров
app.include_router(blocks.router, prefix=settings.API_V1_STR)
app.include_router(transactions.router, prefix=settings.API_V1_STR)
app.include_router(addresses.router, prefix=settings.API_V1_STR)
app.include_router(search.router, prefix=settings.API_V1_STR)
app.include_router(sync.router, prefix=settings.API_V1_STR)
app.include_router(cache.router, prefix=settings.API_V1_STR)


@app.get("/", response_class=HTMLResponse)
async def root(request: Request):
    """Главная страница"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/block/{hash_or_height}", response_class=HTMLResponse)
async def block_page(request: Request, hash_or_height: str):
    """Страница блока"""
    db = next(get_db())
    block_service = BlockService(db)

    # Попробуем получить блок по хэшу или высоте
    try:
        height = int(hash_or_height)
        block = await block_service.get_block_by_height(height)
    except ValueError:
        block = await block_service.get_block_by_hash(hash_or_height)

    return templates.TemplateResponse(
        "block.html", {"request": request, "block": block}
    )


@app.get("/tx/{txid}", response_class=HTMLResponse)
async def transaction_page(request: Request, txid: str):
    """Страница транзакции"""
    db = next(get_db())
    tx_service = TransactionService(db)
    tx = tx_service.get_or_fetch_transaction(txid)

    return templates.TemplateResponse(
        "transaction.html", {"request": request, "tx": tx}
    )


@app.get("/address/{address}", response_class=HTMLResponse)
async def address_page(request: Request, address: str):
    """Страница адреса"""
    db = next(get_db())
    addr = db.query(Address).filter(Address.address == address).first()

    return templates.TemplateResponse(
        "address.html", {"request": request, "address": addr}
    )


@app.get("/blocks", response_class=HTMLResponse)
async def blocks_page(request: Request):
    """Страница списка блоков"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/transactions", response_class=HTMLResponse)
async def transactions_page(request: Request):
    """Страница списка транзакций"""
    return templates.TemplateResponse("index.html", {"request": request})


@app.get("/search", response_class=HTMLResponse)
async def search_page(request: Request, q: str = ""):
    """Страница поиска"""
    if not q:
        return templates.TemplateResponse(
            "components/search_results.html",
            {"request": request, "results": None, "query": ""},
        )

    db = next(get_db())
    block_service = BlockService(db)
    tx_service = TransactionService(db)

    results = {"blocks": [], "transactions": [], "addresses": []}

    # Поиск блоков
    try:
        height = int(q)
        block = await block_service.get_block_by_height(height)
        if block:
            results["blocks"].append(block)
    except ValueError:
        block = await block_service.get_block_by_hash(q)
        if block:
            results["blocks"].append(block)

    # Поиск транзакций
    tx = tx_service.get_transaction_by_txid(q)
    if tx:
        results["transactions"].append(tx)

    # Поиск адресов
    addr = db.query(Address).filter(Address.address == q).first()
    if addr:
        results["addresses"].append(addr)

    return templates.TemplateResponse(
        "components/search_results.html",
        {"request": request, "results": results, "query": q},
    )


@app.get("/components/latest-blocks", response_class=HTMLResponse)
async def latest_blocks_component(request: Request, page: int = 1):
    """HTMX компонент последних блоков"""
    db = next(get_db())
    block_service = BlockService(db)

    limit = 10
    offset = (page - 1) * limit
    blocks = block_service.get_latest_blocks(limit=limit, offset=offset)

    return templates.TemplateResponse(
        "components/block_list.html",
        {
            "request": request,
            "blocks": blocks,
            "page": page,
            "has_more": len(blocks) == limit,
        },
    )


@app.get("/components/latest-transactions", response_class=HTMLResponse)
async def latest_transactions_component(request: Request, page: int = 1):
    """HTMX компонент последних транзакций"""
    db = next(get_db())
    tx_service = TransactionService(db)

    limit = 10
    offset = (page - 1) * limit
    transactions, total = await tx_service.get_latest_transactions(
        limit=limit, offset=offset
    )

    return templates.TemplateResponse(
        "components/tx_list.html",
        {
            "request": request,
            "transactions": transactions,
            "page": page,
            "has_more": len(transactions) == limit,
        },
    )


@app.get("/components/block-transactions", response_class=HTMLResponse)
async def block_transactions_component(request: Request, hash: str):
    """HTMX компонент транзакций блока"""
    db = next(get_db())

    # Получаем транзакции блока напрямую из БД
    from app.models.transaction import Transaction

    transactions = (
        db.query(Transaction)
        .filter(Transaction.block_hash == hash)
        .order_by(Transaction.id)
        .all()
    )

    return templates.TemplateResponse(
        "components/tx_list.html",
        {
            "request": request,
            "transactions": transactions,
            "page": 1,
            "has_more": False,
        },
    )


@app.get("/components/address-transactions", response_class=HTMLResponse)
async def address_transactions_component(request: Request, address: str):
    """HTMX компонент транзакций адреса"""
    db = next(get_db())
    tx_service = TransactionService(db)

    # get_transactions_by_address возвращает словарь с ключом 'transactions'
    result = tx_service.get_transactions_by_address(address, page=1, per_page=50)
    transactions = result["transactions"]

    return templates.TemplateResponse(
        "components/tx_list.html",
        {
            "request": request,
            "transactions": transactions,
            "page": 1,
            "has_more": result.get("has_next", False),
        },
    )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": settings.PROJECT_NAME}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
