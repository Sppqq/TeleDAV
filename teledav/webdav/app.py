from fastapi import FastAPI
from wsgidav.wsgidav_app import WsgiDAVApp
from fastapi.middleware.wsgi import WSGIMiddleware

from teledav.config import settings
from teledav.webdav.provider import TelegramDAVProvider

# --- WsgiDAVApp Configuration ---
dav_config = {
    "provider_mapping": {
        "/": TelegramDAVProvider(),
    },
    "http_authenticator": {
        "domain_controller": None,  # Use SimpleDomainController
        "accept_basic": True,
        "accept_digest": False,
        "default_to_digest": False,
    },
    "simple_dc": {
        "user_mapping": {
            "*": {settings.dav_username: {"password": settings.dav_password}}
        }
    },
    "verbose": 1,
    "logging": {"enable": True},
    "cors": {
        "enabled": True,
        "allow_origin": "*",
        "allow_methods": "*",
        "allow_headers": "*",
        "expose_headers": "*",
    },
}

# --- FastAPI Application ---
app = FastAPI(title="TeleDAV")

# Create the WsgiDAVApp
wsgidav_app = WsgiDAVApp(dav_config)

# Mount the WsgiDAVApp as a WSGI middleware
app.mount("/", WSGIMiddleware(wsgidav_app))


@app.on_event("startup")
async def startup_event():
    # You can add any startup logic here if needed
    pass


@app.get("/health")
async def health_check():
    return {"status": "ok"}
