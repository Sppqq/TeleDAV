"""
TeleDAV - WebDAV сервер с поддержкой Telegram для хранения файлов.

Этот модуль запускает FastAPI приложение с WebDAV поддержкой.
"""
import asyncio
import logging
import uvicorn
from aiogram import Bot, Dispatcher
from wsgidav.wsgidav_app import WsgiDAVApp
from teledav.webdav.provider import TeleDAVProvider
from wsgidav.http_authenticator import HTTPAuthenticator

from teledav.webdav.app import app
from teledav.db.models import create_tables, AsyncSessionLocal, User
from teledav.config import settings
from teledav.bot.handlers import bot_router
from sqlalchemy import select
import hashlib

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)
logging.getLogger("wsgidav").setLevel(logging.WARNING)
logging.getLogger("aiogram").setLevel(logging.WARNING)

def hash_password(password: str) -> str:
    """Хеширование пароля"""
    return hashlib.sha256(password.encode()).hexdigest()

class TeledavDomainController:
    def __init__(self, loop):
        self.loop = loop

    async def get_user_dict(self, realm, username, environ):
        async with AsyncSessionLocal() as session:
            result = await session.execute(select(User).where(User.username == username))
            user = result.scalars().first()
            if user:
                return {"password_hash": user.password_hash}
        return None

    def require_authentication(self, realm, environ):
        return True

    def _get_user_dict_sync(self, realm, username, environ):
        future = asyncio.run_coroutine_threadsafe(self.get_user_dict(realm, username, environ), self.loop)
        try:
            return future.result(timeout=10)
        except Exception as e:
            logger.error(f"Error in _get_user_dict_sync: {e}")
            return None

    def is_realm_user(self, realm, username, environ):
        return self._get_user_dict_sync(realm, username, environ) is not None

    def get_realm_user_data(self, realm, username, environ):
        user = self._get_user_dict_sync(realm, username, environ)
        if user:
            return {"password": user["password_hash"]}
        return None

    def auth_user_data(self, realm, username, password, environ):
        user_data = self.get_realm_user_data(realm, username, environ)
        if user_data and user_data["password"] == hash_password(password):
            return user_data
        return None

async def run_bot(dp: Dispatcher, bot: Bot):
    """Запуск бота в фоновом режиме"""
    logger.info("🤖 Bot is starting...")
    try:
        await dp.start_polling(bot)
    except Exception as e:
        logger.error(f"❌ Bot error: {e}")
    finally:
        await bot.session.close()
        logger.info("🤖 Bot stopped.")

async def main():
    """
    Основная функция для инициализации БД и запуска сервера.
    """
    logger.info("=" * 60)
    logger.info("🚀 TeleDAV - WebDAV Server with Telegram Storage")
    logger.info("=" * 60)
    
    await create_tables()
    logger.info("✅ База данных успешно инициализирована")

    loop = asyncio.get_event_loop()

    # Настройка бота
    bot = Bot(token=settings.bot_token)
    dp = Dispatcher()
    dp.include_router(bot_router)

    # Настройка WebDAV
    dav_config = {
        "provider_mapping": {"/": TeleDAVProvider(loop)},
        "http_authenticator": {
            "HTTPAuthenticator": {
                "domain_controller": TeledavDomainController(loop),
                "accept_basic": True,
                "accept_digest": False,
                "default_to_digest": False,
                "realm": "Teledav"
            }
        },
        "verbose": 1,
    }
    dav_app = WsgiDAVApp(dav_config)
    app.mount("/webdav", dav_app)

    # Настройка и запуск uvicorn
    config = uvicorn.Config(app, host=settings.dav_host, port=settings.dav_port, log_level="info")
    server = uvicorn.Server(config)
    
    logger.info("=" * 60)
    logger.info(f"📡 FastAPI (Web UI) server running on http://{settings.dav_host}:{settings.dav_port}")
    logger.info(f"🔐 WebDAV server running on http://{settings.dav_host}:{settings.dav_port}/webdav")
    logger.info("=" * 60)
    
    bot_task = asyncio.create_task(run_bot(dp, bot))

    try:
        await server.serve()
    except KeyboardInterrupt:
        logger.info("⏸️  Сервер остановлен пользователем")
    finally:
        bot_task.cancel()

if __name__ == "__main__":
    asyncio.run(main())
