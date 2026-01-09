from pathlib import Path
from sqlalchemy.future import select
from sqlalchemy.orm import selectinload
from sqlalchemy.ext.asyncio import AsyncSession

from teledav.db.models import FileSystemNode, FileChunk


async def get_node_by_path(db: AsyncSession, path: str):
    stmt = (
        select(FileSystemNode)
        .where(FileSystemNode.path == path)
        .options(selectinload(FileSystemNode.chunks))
    )
    result = await db.execute(stmt)
    return result.scalars().first()


async def get_children(db: AsyncSession, path: str):
    stmt = select(FileSystemNode).where(FileSystemNode.parent_path == path)
    result = await db.execute(stmt)
    return result.scalars().all()


async def create_node(
    db: AsyncSession, path: str, is_collection: bool = False, topic_id: int = None, size: int = 0
):
    p = Path(path)
    parent_path = str(p.parent)
    node = FileSystemNode(
        path=path,
        parent_path=parent_path,
        name=p.name,
        is_collection=is_collection,
        telegram_topic_id=topic_id,
        size=size,
    )
    db.add(node)
    await db.commit()
    await db.refresh(node)
    return node


async def delete_node(db: AsyncSession, path: str):
    node = await get_node_by_path(db, path)
    if node:
        await db.delete(node)
        await db.commit()
    return node


async def add_chunk(db: AsyncSession, node: FileSystemNode, message_id: int, telegram_file_id: str, order: int):
    chunk = FileChunk(
        node_id=node.id,
        telegram_message_id=message_id,
        telegram_file_id=telegram_file_id,
        chunk_order=order,
    )
    db.add(chunk)
    await db.commit()
    await db.refresh(chunk)
    return chunk
