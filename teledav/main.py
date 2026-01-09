"""
TeleDAV - WebDAV сервер с поддержкой Telegram для хранения файлов.

Этот модуль запускает FastAPI приложение с WebDAV поддержкой.
"""
import asyncio
import logging
import uvicorn

from teledav.webdav.app import app
from teledav.db.models import create_tables
from teledav.config import settings

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

logger = logging.getLogger(__name__)

# Подавляем излишние логи от библиотек
logging.getLogger("wsgidav").setLevel(logging.WARNING)
logging.getLogger("aiogram").setLevel(logging.WARNING)


async def main():
    """
    Основная функция для инициализации БД и запуска сервера.
    """
    logger.info("=" * 60)
    logger.info("🚀 TeleDAV - WebDAV Server with Telegram Storage")
    logger.info("=" * 60)
    
    # Инициализируем БД
    logger.info("Инициализирую базу данных...")
    try:
        await create_tables()
        logger.info("✅ База данных успешно инициализирована")
    except Exception as e:
        logger.error(f"❌ Ошибка при инициализации БД: {e}")
        raise

    # Настройка и запуск uvicorn
    config = uvicorn.Config(
        app,
        host=settings.dav_host,
        port=settings.dav_port,
        log_level="info",
        access_log=True,
    )
    
    server = uvicorn.Server(config)
    
    logger.info("=" * 60)
    logger.info(f"📡 WebDAV сервер запущен на {settings.dav_host}:{settings.dav_port}")
    logger.info(f"👤 Пользователь: {settings.dav_username}")
    logger.info("🔐 Используется Basic Auth")
    logger.info("=" * 60)
    
    try:
        await server.serve()
    except KeyboardInterrupt:
        logger.info("⏸️  Сервер остановлен пользователем")
    except Exception as e:
        logger.error(f"❌ Ошибка при запуске сервера: {e}")
        raise


if __name__ == "__main__":
    asyncio.run(main())
