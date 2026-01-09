from typing import AsyncGenerator, BinaryIO

from teledav.config import settings


async def read_chunks(
    fp: BinaryIO, chunk_size: int = settings.chunk_size
) -> AsyncGenerator[bytes, None]:
    """
    Asynchronously read a file-like object in chunks.
    """
    while True:
        chunk = fp.read(chunk_size)
        if not chunk:
            break
        yield chunk
