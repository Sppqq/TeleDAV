import asyncio
import logging
from typing import BinaryIO, List, Optional
from io import BytesIO

from aiogram import Bot
from aiogram.types import BufferedInputFile
from aiogram.exceptions import TelegramAPIError

from teledav.config import settings

logger = logging.getLogger(__name__)


class TelegramService:
    """Сервис для работы с Telegram ботом"""
    
    def __init__(self, bot: Bot):
        self.bot = bot

    async def create_topic(self, name: str) -> Optional[int]:
        """Создать новую тему (Topic) в группе"""
        try:
            topic = await self.bot.create_forum_topic(
                chat_id=settings.chat_id, name=name
            )
            logger.info(f"Created topic '{name}' with ID: {topic.message_thread_id}")
            return topic.message_thread_id
        except TelegramAPIError as e:
            logger.error(f"Could not create topic '{name}': {e}")
            return None

    async def delete_topic(self, topic_id: int) -> bool:
        """Удалить тему и все сообщения в ней"""
        try:
            await self.bot.delete_forum_topic(
                chat_id=settings.chat_id, message_thread_id=topic_id
            )
            logger.info(f"Deleted topic with ID: {topic_id}")
            return True
        except TelegramAPIError as e:
            logger.error(f"Could not delete topic {topic_id}: {e}")
            return False

    async def upload_chunk(
        self, topic_id: int, data: bytes, file_name: str, chunk_number: int = 0
    ) -> Optional[tuple]:
        """Загрузить часть файла"""
        try:
            document = BufferedInputFile(data, filename=f"{file_name}.part{chunk_number}")
            message = await self.bot.send_document(
                chat_id=settings.chat_id,
                message_thread_id=topic_id,
                document=document,
                caption=f"Part {chunk_number + 1}",
                disable_notification=True,
            )
            logger.info(f"Telegram message object: {message}")
            if message.document:
                logger.info(f"Uploaded chunk {chunk_number} for '{file_name}'")
                return message.message_id, message.document.file_id
            else:
                logger.warning(f"message.document is None for chunk {chunk_number} of '{file_name}'")
            return None
        except TelegramAPIError as e:
            logger.error(f"Could not upload chunk {chunk_number} for '{file_name}': {e}")
            return None

    async def upload_chunks_parallel(
        self, topic_id: int, chunks: List[bytes], file_name: str
    ) -> List[Optional[tuple]]:
        """Загрузить все части файла параллельно"""
        tasks = [
            self.upload_chunk(topic_id, chunk, file_name, i)
            for i, chunk in enumerate(chunks)
        ]
        results = await asyncio.gather(*tasks)
        return results

    async def delete_files(self, message_ids: List[int]) -> bool:
        """Удалить несколько сообщений (части файлов)"""
        try:
            await self.bot.delete_messages(
                chat_id=settings.chat_id, message_ids=message_ids
            )
            logger.info(f"Deleted {len(message_ids)} messages")
            return True
        except TelegramAPIError as e:
            logger.error(f"Could not delete messages {message_ids}: {e}")
            return False

    async def download_chunk(self, file_id: str) -> Optional[bytes]:
        """Скачать часть файла из Telegram"""
        try:
            file_info = await self.bot.get_file(file_id)
            if file_info.file_path:
                return await self.bot.download_file(file_info.file_path)
        except TelegramAPIError as e:
            logger.error(f"Could not download chunk with file_id {file_id}: {e}")
        return None

    async def get_message(self, message_id: int):
        """Получить сообщение по ID"""
        try:
            return await self.bot.get_message(
                chat_id=settings.chat_id,
                message_id=message_id
            )
        except TelegramAPIError as e:
            logger.error(f"Could not get message {message_id}: {e}")
            return None


_bot = Bot(token=settings.bot_token)
telegram_service = TelegramService(_bot)
