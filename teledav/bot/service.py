import asyncio
import logging
from typing import BinaryIO

from aiogram import Bot
from aiogram.types import BufferedInputFile
from aiogram.exceptions import TelegramAPIError

from teledav.config import settings

logger = logging.getLogger(__name__)


class TelegramService:
    def __init__(self, bot: Bot):
        self.bot = bot

    async def create_topic(self, name: str) -> int | None:
        try:
            topic = await self.bot.create_forum_topic(
                chat_id=settings.chat_id, name=name
            )
            return topic.message_thread_id
        except TelegramAPIError as e:
            logger.error(f"Could not create topic '{name}': {e}")
            return None

    async def delete_topic(self, topic_id: int) -> bool:
        try:
            return await self.bot.delete_forum_topic(
                chat_id=settings.chat_id, message_thread_id=topic_id
            )
        except TelegramAPIError as e:
            logger.error(f"Could not delete topic {topic_id}: {e}")
            return False

    async def upload_chunk(
        self, topic_id: int, data: bytes, file_name: str
    ) -> tuple[int, str] | None:
        try:
            document = BufferedInputFile(data, filename=file_name)
            message = await self.bot.send_document(
                chat_id=settings.chat_id,
                message_thread_id=topic_id,
                document=document,
                disable_notification=True,
            )
            if message.document:
                return message.message_id, message.document.file_id
            return None
        except TelegramAPIError as e:
            logger.error(f"Could not upload chunk for '{file_name}': {e}")
            return None

    async def delete_files(self, message_ids: list[int]) -> bool:
        try:
            await self.bot.delete_messages(
                chat_id=settings.chat_id, message_ids=message_ids
            )
            return True
        except TelegramAPIError as e:
            logger.error(f"Could not delete messages {message_ids}: {e}")
            return False

    async def download_chunk(self, file_id: str) -> bytes | None:
        try:
            file_info = await self.bot.get_file(file_id)
            if file_info.file_path:
                return await self.bot.download_file(file_info.file_path)
        except TelegramAPIError as e:
            logger.error(f"Could not download chunk with file_id {file_id}: {e}")
        return None


_bot = Bot(token=settings.bot_token)
telegram_service = TelegramService(_bot)
