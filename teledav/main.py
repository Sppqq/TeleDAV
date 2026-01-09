import asyncio
import logging
import uvicorn

from teledav.webdav.app import app
from teledav.db.models import create_tables
from teledav.config import settings

# Configure logging
logging.basicConfig(level=logging.INFO)
logging.getLogger("wsgidav").setLevel(logging.WARNING)


async def main():
    """
    Main function to initialize the database and run the server.
    """
    print("Initializing database...")
    await create_tables()
    print("Database initialized.")

    config = uvicorn.Config(
        app,
        host=settings.dav_host,
        port=settings.dav_port,
        log_level="info",
    )
    server = uvicorn.Server(config)
    
    print(f"Starting server on {settings.dav_host}:{settings.dav_port}")
    await server.serve()


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        print("Server stopped.")
