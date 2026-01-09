"""
WebDAV провайдер для работы с файловой системой.
Взаимодействует с Telegram через бот для хранения файлов.
"""
import asyncio
import logging
import io
from typing import List, Optional
from wsgidav.dav_provider import DAVProvider, DAVCollection, DAVNullResource
from wsgidav.util import join_path

from teledav.db.models import AsyncSessionLocal, File, Folder
from teledav.db.service import DatabaseService
from teledav.bot.service import telegram_service
from teledav.utils.chunking import read_chunks_from_stream, calculate_chunks, CHUNK_SIZE
from teledav.config import settings

logger = logging.getLogger(__name__)

class TeleDAVResource(DAVNullResource):
    """Ресурс WebDAV - представляет файл"""

    def __init__(self, path: str, environ: dict, file: Optional[File] = None):
        super().__init__(path, environ)
        self.file = file

    def get_content_length(self):
        """Получить размер файла"""
        if self.file:
            return self.file.size
        return None

    def get_content_type(self):
        """Получить MIME-тип"""
        if self.file:
            return self.file.mime_type
        return "application/octet-stream"

    def get_display_name(self):
        """Получить название файла"""
        if self.file:
            return self.file.name
        return self.path.split("/")[-1]

    def get_last_modified(self):
        """Получить время последнего изменения"""
        if self.file and self.file.updated_at:
            return self.file.updated_at.timestamp()
        return None

    async def get_content(self):
        """Получить содержимое файла"""
        if not self.file:
            return None

        chunks = []
        async with AsyncSessionLocal() as session:
            db_service = DatabaseService(session)
            file_chunks = await db_service.get_chunks_by_file(self.file.id)

            # Загружаем все части параллельно
            for chunk in file_chunks:
                if chunk.message_id:
                    chunk_data = await self._download_chunk(chunk)
                    if chunk_data:
                        chunks.append(chunk_data)

        # Объединяем все части
        return b"".join(chunks)

    async def _download_chunk(self, chunk):
        """Загрузить часть файла из Telegram"""
        try:
            message = await telegram_service.get_message(chunk.message_id)
            if message and message.document:
                return await telegram_service.download_chunk(message.document.file_id)
        except Exception as e:
            logger.error(f"Error downloading chunk {chunk.id}: {e}")
        return None

    async def put_content(self, content_stream, content_type: str = None, content_length: int = None):
        """Загрузить файл"""
        # Создаём временный буфер из потока
        buffer = io.BytesIO()
        while True:
            chunk = content_stream.read(1024 * 1024)  # 1MB за раз
            if not chunk:
                break
            buffer.write(chunk)

        buffer.seek(0)
        file_size = buffer.getbuffer().nbytes

        async with AsyncSessionLocal() as session:
            db_service = DatabaseService(session)

            # Если файл уже существует, удаляем его
            existing_file = await db_service.get_file_by_path(self.path)
            if existing_file:
                await self._delete_file(db_service, existing_file)

            # Получаем папку или создаем её
            parent_path = "/".join(self.path.split("/")[:-1])
            folder = await db_service.get_folder_by_path(parent_path)
            if not folder:
                folder_name = parent_path.split("/")[-1]
                folder = await db_service.create_folder(folder_name, parent_path)
                # Создаем тему в Telegram
                topic_id = await telegram_service.create_topic(folder_name)
                if topic_id:
                    await db_service.update_folder_topic(folder.id, topic_id)

            # Создаем запись о файле
            file_name = self.path.split("/")[-1]
            file = await db_service.create_file(
                folder.id,
                file_name,
                self.path,
                file_size,
                content_type or "application/octet-stream"
            )

            # Разделяем файл на части и загружаем
            chunk_count = calculate_chunks(file_size)
            chunks_data = []

            async for chunk_number, chunk_data in read_chunks_from_stream(buffer, file_size):
                chunks_data.append(chunk_data)
                # Создаем запись о части в БД
                chunk = await db_service.create_chunk(file.id, chunk_number, len(chunk_data))

            # Загружаем все части параллельно в Telegram
            if folder.topic_id:
                upload_results = await telegram_service.upload_chunks_parallel(
                    folder.topic_id,
                    chunks_data,
                    file_name
                )

                # Сохраняем ID сообщений
                for i, result in enumerate(upload_results):
                    if result:
                        message_id, file_id = result
                        await db_service.update_chunk_message_ids(
                            # Получаем chunk с нужным номером
                            (await db_service.get_chunks_by_file(file.id))[i].id,
                            message_id,
                            folder.topic_id
                        )

    async def delete(self):
        """Удалить файл"""
        async with AsyncSessionLocal() as session:
            db_service = DatabaseService(session)
            file = await db_service.get_file_by_path(self.path)
            if file:
                await self._delete_file(db_service, file)

    async def _delete_file(self, db_service: DatabaseService, file: File):
        """Удалить файл и все его части из Telegram"""
        chunks = await db_service.get_chunks_by_file(file.id)
        message_ids = [c.message_id for c in chunks if c.message_id]

        if message_ids:
            await telegram_service.delete_files(message_ids)

        await db_service.delete_file(file.id)


class TeleDAVCollection(DAVCollection):
    """Коллекция WebDAV - представляет папку"""

    def __init__(self, path: str, environ: dict, folder: Optional[Folder] = None):
        super().__init__(path, environ)
        self.folder = folder

    def get_display_name(self):
        """Получить название папки"""
        if self.folder:
            return self.folder.name
        return self.path.split("/")[-1]

    def get_member_list(self):
        """Получить список элементов в папке"""
        async def _get_members():
            async with AsyncSessionLocal() as session:
                db_service = DatabaseService(session)
                items = []

                if self.folder:
                    # Получаем файлы
                    files = await db_service.get_files_by_folder(self.folder.id)
                    for file in files:
                        items.append(
                            TeleDAVResource(
                                join_path(self.path, file.name),
                                self.environ,
                                file
                            )
                        )

                return items

        return asyncio.run(_get_members())

    async def mkcol(self, name: str) -> "TeleDAVCollection":
        """Создать папку"""
        new_path = join_path(self.path, name)

        async with AsyncSessionLocal() as session:
            db_service = DatabaseService(session)

            # Создаем папку в БД
            folder = await db_service.create_folder(name, new_path)

            # Создаем тему в Telegram
            topic_id = await telegram_service.create_topic(name)
            if topic_id:
                await db_service.update_folder_topic(folder.id, topic_id)

            return TeleDAVCollection(new_path, self.environ, folder)


class TeleDAVProvider(DAVProvider):
    """WebDAV провайдер для TeleDAV"""

    def __init__(self, environ: dict):
        super().__init__(environ)
        self.root_path = "/"

    async def _get_resource(self, path: str):
        """Получить ресурс (файл или папку) по пути"""
        async with AsyncSessionLocal() as session:
            db_service = DatabaseService(session)

            # Проверяем файл
            file = await db_service.get_file_by_path(path)
            if file:
                return TeleDAVResource(path, self.environ, file)

            # Проверяем папку
            folder = await db_service.get_folder_by_path(path)
            if folder:
                return TeleDAVCollection(path, self.environ, folder)

        return None

    def get_resource_inst(self, path: str, environ: dict):
        """Получить экземпляр ресурса"""
        resource = asyncio.run(self._get_resource(path))
        return resource

    async def delete(self, path: str):
        """Удалить ресурс"""
        async with AsyncSessionLocal() as session:
            db_service = DatabaseService(session)

            # Пытаемся удалить как файл
            file = await db_service.get_file_by_path(path)
            if file:
                chunks = await db_service.get_chunks_by_file(file.id)
                message_ids = [c.message_id for c in chunks if c.message_id]
                if message_ids:
                    await telegram_service.delete_files(message_ids)
                await db_service.delete_file(file.id)
                return

            # Пытаемся удалить как папку
            folder = await db_service.get_folder_by_path(path)
            if folder:
                if folder.topic_id:
                    await telegram_service.delete_topic(folder.topic_id)
                await db_service.delete_folder(folder.id)
