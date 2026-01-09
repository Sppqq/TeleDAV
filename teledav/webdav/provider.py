"""
Простой WebDAV провайдер для TeleDAV.
Хранит файлы в Telegram через бот.
"""
import asyncio
import logging
from typing import Optional
from wsgidav.dav_provider import DAVProvider

from teledav.db.models import AsyncSessionLocal, File, Folder
from teledav.db.service import DatabaseService
from teledav.bot.service import telegram_service

logger = logging.getLogger(__name__)


class TeleDAVProvider(DAVProvider):
    """WebDAV провайдер для работы с Telegram как хранилищем"""

    def __init__(self, environ):
        super().__init__(environ)
        self.root_path = "/"

    def get_resource_inst(self, path, environ):
        """
        Получить ресурс по пути.
        Возвращает None если ресурс не найден.
        """
        try:
            # Запускаем асинхронный код
            resource = asyncio.run(self._get_resource_async(path, environ))
            return resource
        except Exception as e:
            logger.error(f"Error getting resource at {path}: {e}")
            return None

    async def _get_resource_async(self, path, environ):
        """Асинхронное получение ресурса"""
        async with AsyncSessionLocal() as session:
            db_service = DatabaseService(session)
            
            # Нормализуем путь
            path = path.strip("/") or "/"
            
            # Проверяем файл
            file = await db_service.get_file_by_path(path)
            if file:
                return FileResource(environ, path, file)
            
            # Проверяем папку
            folder = await db_service.get_folder_by_path(path)
            if folder:
                return FolderResource(environ, path, folder, self)
            
            # Если ничего не найдено
            if path == "/":
                return FolderResource(environ, path, None, self)
            
            return None


class FileResource:
    """Ресурс WebDAV для файла"""
    
    def __init__(self, environ, path, file: Optional[File]):
        self.environ = environ
        self.path = path
        self.file = file
        self.is_collection = False
    
    def get_display_name(self):
        """Получить название файла"""
        if self.file:
            return self.file.name
        return self.path.split("/")[-1]
    
    def get_content_length(self):
        """Получить размер файла"""
        if self.file:
            return self.file.size
        return 0
    
    def get_content_type(self):
        """Получить MIME-тип"""
        if self.file:
            return self.file.mime_type
        return "application/octet-stream"
    
    def get_last_modified(self):
        """Получить время последнего изменения"""
        if self.file and self.file.updated_at:
            return self.file.updated_at.timestamp()
        return 0


class FolderResource:
    """Ресурс WebDAV для папки"""
    
    def __init__(self, environ, path, folder: Optional[Folder], provider):
        self.environ = environ
        self.path = path
        self.folder = folder
        self.provider = provider
        self.is_collection = True
    
    def get_display_name(self):
        """Получить название папки"""
        if self.folder:
            return self.folder.name
        if self.path == "/":
            return "TeleDAV"
        return self.path.split("/")[-1]
    
    def get_member_list(self):
        """Получить список элементов в папке"""
        try:
            members = asyncio.run(self._get_members_async())
            return members
        except Exception as e:
            logger.error(f"Error getting members of {self.path}: {e}")
            return []
    
    async def _get_members_async(self):
        """Асинхронное получение списка элементов"""
        members = []
        async with AsyncSessionLocal() as session:
            db_service = DatabaseService(session)
            
            if self.folder:
                # Получаем файлы в папке
                files = await db_service.get_files_by_folder(self.folder.id)
                for file in files:
                    file_path = f"{self.path.rstrip('/')}/{file.name}"
                    members.append(FileResource(self.environ, file_path, file))
        
        return members
    
    def mkcol(self):
        """Создать подпапку"""
        # Сейчас не реализуется
        pass
    
    def delete(self):
        """Удалить папку"""
        # Сейчас не реализуется
        pass
