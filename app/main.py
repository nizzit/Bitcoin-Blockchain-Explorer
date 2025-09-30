"""
Главное FastAPI приложение Bitcoin Blockchain Explorer
"""

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.api import addresses, blocks, search, transactions
from app.config import settings

# Создаем FastAPI приложение
app = FastAPI(
    title=settings.PROJECT_NAME,
    version=settings.VERSION,
    description="Минималистичный blockchain explorer для Bitcoin",
    docs_url="/docs",
    redoc_url="/redoc",
    debug=True,
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


@app.get("/")
async def root():
    """Главная страница"""
    return {"message": "Bitcoin Blockchain Explorer", "version": settings.VERSION}


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "service": settings.PROJECT_NAME}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("app.main:app", host="0.0.0.0", port=8000, reload=settings.DEBUG)
