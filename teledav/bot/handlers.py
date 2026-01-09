from aiogram import Router
from aiogram.filters import Command
from aiogram.types import Message

from teledav.db.models import AsyncSessionLocal
from teledav.db.service import DatabaseService
from teledav.config import settings
from teledav.bot.service import TelegramService

bot_router = Router()


@bot_router.message(Command(commands=["start"]))
async def start_command(message: Message):
    """Handler for /start command"""
    await message.answer(
        "Welcome to TeleDAV bot!\n"
        "I can help you manage your files.\n"
        "Available commands:\n"
        "/help - Show this help message\n"
        "/list - List your files\n"
        "/delete <filename> - Delete a file"
    )


@bot_router.message(Command(commands=["help"]))
async def help_command(message: Message):
    """Handler for /help command"""
    await message.answer(
        "Available commands:\n"
        "/start - Show welcome message\n"
        "/list - List your files\n"
        "/delete <filename> - Delete a file"
    )


@bot_router.message(Command(commands=["list"]))
async def list_command(message: Message):
    """Handler for /list command"""
    if message.from_user.id != settings.admin_user_id:
        await message.answer("You are not authorized to use this command.")
        return

    async with AsyncSessionLocal() as session:
        db_service = DatabaseService(session)
        files = await db_service.get_all_files()

        if not files:
            await message.answer("No files found.")
            return

        response = "Files:\n"
        for file in files:
            response += f"- `{file.name}` ({file.size / 1024:.2f} KB)\n"

        await message.answer(response, parse_mode="Markdown")


@bot_router.message(Command(commands=["delete"]))
async def delete_command(message: Message):
    """Handler for /delete command"""
    if message.from_user.id != settings.admin_user_id:
        await message.answer("You are not authorized to use this command.")
        return

    args = message.text.split()
    if len(args) < 2:
        await message.answer("Usage: /delete <filename>")
        return

    file_name = args[1]
    async with AsyncSessionLocal() as session:
        db_service = DatabaseService(session)
        file = await db_service.get_file_by_name(file_name)

        if not file:
            await message.answer(f"File '{file_name}' not found.")
            return

        chunks = await db_service.get_chunks_by_file(file.id)
        message_ids = [c.message_id for c in chunks if c.message_id]
        if message_ids:
            await telegram_service.delete_files(message_ids)

        await db_service.delete_file(file.id)
        await message.answer(f"File '{file_name}' deleted successfully.")
