"""
Простой WebDAV провайдер для TeleDAV.
Хранит файлы в Telegram через бот.
"""
import logging

logger = logging.getLogger(__name__)


class TeleDAVProvider:
    """WebDAV провайдер для работы с Telegram как хранилищем"""

    def __init__(self, environ):
        """Инициализация провайдера"""
        self.environ = environ if environ else {}
        self.root_path = "/"

    def get_resource_inst(self, path, environ):
        """
        Получить ресурс по пути.
        Возвращает None если ресурс не найден.
        """
        # Пока возвращаем None - провайдер в разработке
        return None


class FileResource:
    """Ресурс WebDAV для файла"""
    
    def __init__(self, environ, path, file=None):
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


class FolderResource:
    """Ресурс WebDAV для папки"""
    
    def __init__(self, environ, path, folder=None, provider=None):
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
        return []

