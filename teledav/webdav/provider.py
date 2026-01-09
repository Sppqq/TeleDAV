"""
WebDAV провайдер для работы с файловой системой.
Взаимодействует с Telegram через бот для хранения файлов.
"""
import asyncio
import logging
import io
import os
from typing import List, Optional
from wsgidav.dav_provider import DAVProvider, DAVCollection, _DAVResource
from teledav.db.models import AsyncSessionLocal, File, Folder, User
from teledav.db.service import DatabaseService
from teledav.bot.service import TelegramService
from teledav.config import settings
from sqlalchemy import select
import hashlib

logger = logging.getLogger(__name__)

def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode()).hexdigest()

class TeleDAVResource(_DAVResource):
    """Ресурс WebDAV - представляет файл"""
    def __init__(self, path: str, environ: dict, file: Optional[File] = None):
        super().__init__(path, environ)
        self.file = file
        self.loop = self.provider.loop

    def get_content_length(self):
        return self.file.size if self.file else 0

    def get_content_type(self):
        return self.file.mime_type if self.file else "application/octet-stream"

    def get_display_name(self):
        return self.file.name if self.file else os.path.basename(self.path)

    def get_last_modified(self):
        return self.file.updated_at.timestamp() if self.file and self.file.updated_at else None

    def get_content(self):
        if not self.file:
            return None

        # This part is tricky because wsgidav expects a file-like object
        # We will read all chunks into memory for now.
        future = asyncio.run_coroutine_threadsafe(self._async_get_content(), self.loop)
        return io.BytesIO(future.result())

    async def _async_get_content(self):
        async with AsyncSessionLocal() as session:
            db_service = DatabaseService(session)
            chunks = await db_service.get_chunks_by_file(self.file.id)
            data = bytearray()
            for chunk in chunks:
                if chunk.message_id:
                    chunk_data = await self.telegram_service.download_chunk(str(chunk.message_id))
                    if chunk_data:
                        data.extend(chunk_data)
            return data

    def begin_write(self, content_type=None):
        self.temp_file = io.BytesIO()
        return self.temp_file

    def end_write(self, with_errors):
        if with_errors:
            return

        self.temp_file.seek(0)
        future = asyncio.run_coroutine_threadsafe(
            self._async_put_content(self.temp_file, self.path, self.environ["wsgidav.auth.user_name"]),
            self.loop
        )
        future.result()

    async def _async_put_content(self, buffer, path, username):
        file_size = buffer.getbuffer().nbytes
        async with AsyncSessionLocal() as session:
            db_service = DatabaseService(session)

            user_result = await session.execute(select(User).where(User.username == username))
            user = user_result.scalars().first()
            if not user:
                logger.error(f"User {username} not found")
                return

            parent_path = os.path.dirname(path) or "/"
            folder = await db_service.get_folder_by_path(parent_path, user.id)
            if not folder:
                folder_name = os.path.basename(parent_path) if parent_path != "/" else user.username
                folder = await db_service.create_folder(folder_name, parent_path, user.id)
                topic_id = await self.telegram_service.create_topic(folder_name)
                if topic_id:
                    await db_service.update_folder_topic(folder.id, topic_id, user.id)

            file_name = os.path.basename(path)
            file_obj = await db_service.create_file(folder.id, user.id, file_name, path, file_size)

            chunk_index = 0
            while True:
                chunk_content = buffer.read(settings.chunk_size)
                if not chunk_content: break
                chunk_obj = await db_service.create_chunk(file_obj.id, chunk_index, len(chunk_content))
                result = await self.telegram_service.upload_chunk(folder.topic_id, chunk_content, f"{file_name}.part{chunk_index}")
                if result:
                    await db_service.update_chunk_message_ids(chunk_obj.id, result[0], folder.topic_id)
                chunk_index += 1

class TeleDAVCollection(DAVCollection):
    def __init__(self, path: str, environ: dict, folder: Optional[Folder] = None):
        super().__init__(path, environ)
        self.folder = folder
        self.loop = self.provider.loop

    def get_display_name(self):
        return self.folder.name if self.folder else "Root"

    def get_member_names(self):
        future = asyncio.run_coroutine_threadsafe(self._async_get_member_names(), self.loop)
        return future.result()

    async def _async_get_member_names(self):
        async with AsyncSessionLocal() as session:
            db_service = DatabaseService(session)
            user = await db_service.get_user_by_username(self.environ["wsgidav.auth.user_name"])
            if not user: return []

            current_folder = self.folder or await db_service.get_folder_by_path(self.path, user.id)
            if not current_folder: return []

            files = await db_service.get_files_by_folder(current_folder.id, user.id)
            return [f.name for f in files]

    def get_member(self, name):
        path = os.path.join(self.path, name)
        future = asyncio.run_coroutine_threadsafe(self.provider._get_resource(path, self.environ), self.loop)
        return future.result()

class TeleDAVProvider(DAVProvider):
    def __init__(self, loop):
        super().__init__()
        self.loop = loop

    def get_resource_inst(self, path, environ):
        future = asyncio.run_coroutine_threadsafe(self._get_resource(path, environ), self.loop)
        return future.result()

    async def _get_resource(self, path, environ):
        username = environ.get("wsgidav.auth.user_name")
        if not username: return None

        async with AsyncSessionLocal() as session:
            db = DatabaseService(session)
            user = await db.get_user_by_username(username)
            if not user: return None

            file = await db.get_file_by_path(path, user.id)
            if file: return TeleDAVResource(path, environ, file)

            folder = await db.get_folder_by_path(path, user.id)
            if folder or path == "/":
                return TeleDAVCollection(path, environ, folder)
        return None
