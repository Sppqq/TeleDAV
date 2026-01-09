"""
FastAPI приложение для TeleDAV.
Простой REST API без WebDAV.
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from teledav.config import settings
from teledav.db.models import create_tables

logger = logging.getLogger(__name__)


# Создаем FastAPI приложение
app = FastAPI(
    title="TeleDAV",
    description="Telegram-powered file storage with REST API",
    version="1.0.0"
)

# Добавляем CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    logger.info("Starting TeleDAV server...")
    try:
        await create_tables()
        logger.info("Database initialized successfully")
    except Exception as e:
        logger.error(f"Error initializing database: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при остановке"""
    logger.info("Shutting down TeleDAV server...")


@app.get("/health")
async def health_check():
    """Проверка здоровья приложения"""
    return {"status": "ok", "service": "TeleDAV"}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "TeleDAV - Telegram-powered file storage",
        "version": "1.0.0",
        "endpoints": {
            "health": "/health",
            "docs": "/docs"
        }
    }

