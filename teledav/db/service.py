from typing import List, Optional
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, delete
from teledav.db.models import Folder, File, FileChunk


class DatabaseService:
    """Сервис для работы с БД"""

    def __init__(self, session: AsyncSession):
        self.session = session

    # ==================== FOLDER OPERATIONS ====================

    async def create_folder(self, name: str, path: str, user_id: int) -> Folder:
        """Создать новую папку"""
        folder = Folder(name=name, path=path, user_id=user_id)
        self.session.add(folder)
        await self.session.commit()
        await self.session.refresh(folder)
        return folder

    async def get_folder_by_path(self, path: str, user_id: int) -> Optional[Folder]:
        """Получить папку по пути"""
        result = await self.session.execute(
            select(Folder).where(Folder.path == path, Folder.user_id == user_id)
        )
        return result.scalars().first()

    async def get_folder_by_id(self, folder_id: int, user_id: int = None) -> Optional[Folder]:  
        """Получить папку по ID"""  
        if user_id:  
            result = await self.session.execute(  
                select(Folder).where(Folder.id == folder_id, Folder.user_id == user_id)  
            )  
            return result.scalars().first()  
        return await self.session.get(Folder, folder_id)

    async def get_all_folders(self) -> List[Folder]:
        """Получить все папки"""
        result = await self.session.execute(select(Folder))
        return result.scalars().all()

    async def update_folder_topic(self, folder_id: int, topic_id: int, user_id: int = None) -> Optional[Folder]:  
        """Обновить Telegram Topic ID папки"""  
        folder = await self.get_folder_by_id(folder_id, user_id)  
        if folder:  
            folder.topic_id = topic_id  
            await self.session.commit()  
            await self.session.refresh(folder)  
        return folder

    async def delete_folder(self, folder_id: int) -> bool:
        """Удалить папку и все её файлы"""
        await self.session.execute(
            delete(Folder).where(Folder.id == folder_id)
        )
        await self.session.commit()
        return True

    # ==================== FILE OPERATIONS ====================

    async def create_file(self, folder_id: int, user_id: int, name: str, path: str, size: int, mime_type: str = "application/octet-stream") -> File:
        """Создать новый файл"""
        file = File(
            folder_id=folder_id,
            user_id=user_id,
            name=name,
            path=path,
            size=size,
            mime_type=mime_type
        )
        self.session.add(file)
        await self.session.commit()
        await self.session.refresh(file)
        return file

    async def get_file_by_path(self, path: str, user_id: int) -> Optional[File]:
        """Получить файл по пути"""
        result = await self.session.execute(
            select(File).where(File.path == path, File.user_id == user_id)
        )
        return result.scalars().first()

    async def get_file_by_id(self, file_id: int, user_id: int = None) -> Optional[File]:
        """Получить файл по ID"""
        if user_id:
            result = await self.session.execute(
                select(File).where(File.id == file_id, File.user_id == user_id)
            )
            return result.scalars().first()
        return await self.session.get(File, file_id)

    async def get_files_by_folder(self, folder_id: int, user_id: int) -> List[File]:
        """Получить все файлы в папке"""
        result = await self.session.execute(
            select(File).where(File.folder_id == folder_id, File.user_id == user_id)
        )
        return result.scalars().all()

    async def delete_file(self, file_id: int) -> bool:
        """Удалить файл и все его части"""
        await self.delete_chunks_by_file(file_id)
        await self.session.execute(delete(File).where(File.id == file_id))
        await self.session.commit()
        return True

    # ==================== CHUNK OPERATIONS ====================

    async def create_chunk(self, file_id: int, chunk_number: int, size: int) -> FileChunk:
        """Создать часть файла"""
        chunk = FileChunk(
            file_id=file_id,
            chunk_number=chunk_number,
            size=size
        )
        self.session.add(chunk)
        await self.session.commit()
        await self.session.refresh(chunk)
        return chunk

    async def update_chunk_message_ids(self, chunk_id: int, message_id: int, thread_id: int) -> Optional[FileChunk]:
        """Обновить Telegram Message ID и Thread ID части"""
        chunk = await self.session.get(FileChunk, chunk_id)
        if chunk:
            chunk.message_id = message_id
            chunk.thread_id = thread_id
            await self.session.commit()
            await self.session.refresh(chunk)
        return chunk

    async def get_chunks_by_file(self, file_id: int) -> List[FileChunk]:
        """Получить все части файла"""
        result = await self.session.execute(
            select(FileChunk).where(FileChunk.file_id == file_id).order_by(FileChunk.chunk_number)
        )
        return result.scalars().all()

    async def get_chunk_by_id(self, chunk_id: int) -> Optional[FileChunk]:
        """Получить часть по ID"""
        return await self.session.get(FileChunk, chunk_id)

    async def delete_chunks_by_file(self, file_id: int) -> bool:
        """Удалить все части файла"""
        await self.session.execute(
            delete(FileChunk).where(FileChunk.file_id == file_id)
        )
        await self.session.commit()
        return True
