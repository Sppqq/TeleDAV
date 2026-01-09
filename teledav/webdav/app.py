"""
FastAPI приложение с WebDAV поддержкой.
Интегрирует wsgidav с FastAPI для обслуживания WebDAV запросов.
"""
import logging
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from wsgidav.wsgidav_app import WsgiDAVApp
from wsgidav.dc.base_dc import BaseDomainController
from fastapi.middleware.wsgi import WSGIMiddleware

from teledav.config import settings
from teledav.webdav.provider import TeleDAVProvider
from teledav.db.models import create_tables

logger = logging.getLogger(__name__)


# Контроллер для аутентификации WebDAV
class SimpleDomainControllerImpl(BaseDomainController):
    def __init__(self):
        super().__init__()
        # Добавляем пользователя из конфига
        self.user_map = {
            "*": {
                settings.dav_username: {
                    "password": settings.dav_password
                }
            }
        }

    def get_domain_realm(self, path_info):
        return "TeleDAV"

    def require_authentication(self, realm, environ):
        return True

    def basic_auth_user(self, realm, user_name, password):
        # Проверяем учетные данные
        users = self.user_map.get("*", {})
        if user_name in users:
            stored_pwd = users[user_name].get("password")
            if stored_pwd == password:
                return True
        return False
    
    def supports_http_digest_auth(self):
        """Не поддерживаем digest auth"""
        return False


# Конфигурация WsgiDAVApp
dav_config = {
    "provider_mapping": {
        "/": TeleDAVProvider({}),
    },
    "http_authenticator": {
        "domain_controller": SimpleDomainControllerImpl(),
        "accept_basic": True,
        "accept_digest": False,
        "default_to_digest": False,
    },
    "verbose": 1,
    "logging": {
        "enable": True,
        "level": logging.DEBUG,
    },
    "cors": {
        "enabled": True,
    },
    "dir_browser": {
        "enable": True,
        "icon": True,
    },
}

# Создаем FastAPI приложение
app = FastAPI(
    title="TeleDAV",
    description="WebDAV сервер с поддержкой Telegram для хранения файлов",
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

# Создаем WsgiDAVApp
wsgidav_app = WsgiDAVApp(dav_config)

# Монтируем WebDAV приложение
app.mount("/", WSGIMiddleware(wsgidav_app))


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
    return {"status": "ok"}
