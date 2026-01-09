import asyncio
import logging
from pathlib import Path
from wsgidav.dav_provider import DAVProvider, DAVCollection, DAVResource
from wsgidav.util import join_path

from teledav.db.models import AsyncSessionLocal
from teledav.db import service as db_service
from teledav.bot.service import telegram_service
from teledav.utils.chunking import read_chunks
from teledav.config import settings

logger = logging.getLogger(__name__)


class TelegramFileStreamer:
    def __init__(self, path: str):
        self.path = path
        self._node = None
        self._chunks = []
        self._chunk_iterator = None
        self._current_chunk_data = None
        self._current_chunk_offset = 0
        self.closed = False

    def _initialize(self):
        if self._node is not None:
            return

        async def _fetch_metadata():
            async with AsyncSessionLocal() as db:
                node = await db_service.get_node_by_path(db, self.path)
                if node and not node.is_collection:
                    # The relationship is lazy, so chunks are loaded here
                    chunks_result = await db.execute(
                        select(db_service.FileChunk)
                        .where(db_service.FileChunk.node_id == node.id)
                        .order_by(db_service.FileChunk.chunk_order)
                    )
                    return node, chunks_result.scalars().all()
            return None, []

        self._node, self._chunks = asyncio.run(_fetch_metadata())
        self._chunk_iterator = iter(self._chunks)

    def _fetch_next_chunk_from_telegram(self):
        try:
            next_chunk_info = next(self._chunk_iterator)
            file_id = next_chunk_info.telegram_file_id

            async def _download():
                return await telegram_service.download_chunk(file_id)

            data = asyncio.run(_download())
            if data is None:
                raise IOError(f"Failed to download chunk for file {self.path}")

            self._current_chunk_data = data
            self._current_chunk_offset = 0
            return True

        except StopIteration:
            self._current_chunk_data = None
            return False

    def read(self, size: int = -1) -> bytes:
        if self.closed:
            raise ValueError("I/O operation on closed file")

        self._initialize()
        if not self._node:
            return b""

        # If size is not provided or is negative, read a sensible block size.
        # Don't try to read the whole file.
        effective_size = size if size > 0 else 65536

        result_bytes = bytearray()

        while len(result_bytes) < effective_size:
            if self._current_chunk_data is None or self._current_chunk_offset >= len(self._current_chunk_data):
                if not self._fetch_next_chunk_from_telegram():
                    break  # No more chunks

            remaining_in_chunk = len(self._current_chunk_data) - self._current_chunk_offset
            needed = effective_size - len(result_bytes)
            
            bytes_to_take = min(remaining_in_chunk, needed)
            
            start = self._current_chunk_offset
            end = self._current_chunk_offset + bytes_to_take
            result_bytes.extend(self._current_chunk_data[start:end])
            
            self._current_chunk_offset += bytes_to_take
        
        return bytes(result_bytes)
    
    def __iter__(self):
        return self

    def __next__(self):
        data = self.read(settings.chunk_size)
        if not data:
            raise StopIteration
        return data

    def close(self):
        if not self.closed:
            self.closed = True
            # Cleanup resources if any
            self._node = None
            self._chunks = None
            self._chunk_iterator = None
            self._current_chunk_data = None


class TelegramDAVProvider(DAVProvider):
    def __init__(self):
        super().__init__()
        self.root_path = "/"

    async def _get_node(self, path):
        # Normalize path
        path = "/" + path.strip("/")
        async with AsyncSessionLocal() as db:
            if path == "/":
                # Create a virtual root node
                return db_service.FileSystemNode(path="/", parent_path="", name="", is_collection=True)
            return await db_service.get_node_by_path(db, path)

    def get_member(self, path):
        node = asyncio.run(self._get_node(path))
        if node is None:
            return None
        
        if node.is_collection:
            return DAVCollection(path, self.environ)
        
        return DAVResource(path, self.environ)

    def get_member_names(self, path):
        node = asyncio.run(self._get_node(path))
        if node is None or not node.is_collection:
            return []
        
        async def _fetch_children():
            async with AsyncSessionLocal() as db:
                children = await db_service.get_children(db, path)
                return [child.name for child in children]

        return asyncio.run(_fetch_children())
    
    def get_member_properties(self, path, name):
        # This can be optimized, but for now, it's fine
        return []

    def get_property(self, path, name, default=None):
        # Implement if specific properties are needed
        return default

    def create_collection(self, path):
        path = "/" + path.strip("/")
        
        async def _create():
            topic_id = await telegram_service.create_topic(path)
            if topic_id:
                async with AsyncSessionLocal() as db:
                    await db_service.create_node(db, path, is_collection=True, topic_id=topic_id)
                    return True
            return False

        if not asyncio.run(_create()):
            raise Exception("Failed to create collection")

    def create_resource(self, path):
        path = "/" + path.strip("/")
        
        async def _create():
            p = Path(path)
            parent_path = str(p.parent)
            async with AsyncSessionLocal() as db:
                parent_node = await db_service.get_node_by_path(db, parent_path)
                if not parent_node or not parent_node.is_collection:
                    return None

                node = await db_service.create_node(db, path, is_collection=False, size=0)
                return node, parent_node.telegram_topic_id

        result = asyncio.run(_create())
        if result is None:
            raise Exception(f"Parent collection does not exist for {path}")
        
        node, topic_id = result
        
        content_length = int(self.environ.get("CONTENT_LENGTH", 0))

        async def _upload():
            fp = self.environ["wsgi.input"]
            chunk_num = 0
            async for chunk in read_chunks(fp, settings.chunk_size):
                chunk_num += 1
                file_name = f"{node.name}.part{chunk_num}"
                upload_result = await telegram_service.upload_chunk(topic_id, chunk, file_name)
                
                if not upload_result:
                    # Cleanup logic needed here
                    raise Exception("Failed to upload chunk")

                message_id, file_id = upload_result
                
                async with AsyncSessionLocal() as db:
                    await db_service.add_chunk(db, node, message_id, file_id, chunk_num)
            
            async with AsyncSessionLocal() as db:
                node_to_update = await db_service.get_node_by_path(db, path)
                if node_to_update:
                    node_to_update.size = content_length
                    await db.commit()

        asyncio.run(_upload())

        return self.get_member(path)


    def get_resource_data(self, path):
        node = asyncio.run(self._get_node(path))
        if not node or node.is_collection:
            return None
        return TelegramFileStreamer(path)

    def delete(self, path):
        path = "/" + path.strip("/")

        async def _delete():
            async with AsyncSessionLocal() as db:
                node = await db_service.get_node_by_path(db, path)
                if not node:
                    return False

                if node.is_collection:
                    # Delete all children first
                    children = await db_service.get_children(db, path)
                    for child in children:
                        # This is recursive, could be slow.
                        # A bulk delete would be better.
                        await self.delete(child.path) 
                    
                    if node.telegram_topic_id:
                        await telegram_service.delete_topic(node.telegram_topic_id)
                else:
                    message_ids = [chunk.telegram_message_id for chunk in node.chunks]
                    if message_ids:
                        await telegram_service.delete_files(message_ids)
                
                await db_service.delete_node(db, path)
                return True

        if not asyncio.run(_delete()):
            raise Exception(f"Failed to delete {path}")

    def get_last_modified(self, path):
        node = asyncio.run(self._get_node(path))
        return node.modified_at.timestamp() if node else None

    def get_content_length(self, path):
        node = asyncio.run(self._get_node(path))
        return node.size if node else None

    def get_display_name(self, path):
        node = asyncio.run(self._get_node(path))
        return node.name if node else None

    def is_collection(self, path):
        node = asyncio.run(self._get_node(path))
        return node.is_collection if node else False
