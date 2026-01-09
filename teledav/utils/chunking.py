"""
Утилиты для разделения и сборки файлов по частям.
Лимит Telegram: 50MB на сообщение.
"""
from typing import AsyncGenerator, BinaryIO, List, Tuple
import io

# Максимальный размер части (49.9 МБ, чтобы быть в безопасности)
CHUNK_SIZE = int(49.9 * 1024 * 1024)  # 49.9 MB


def calculate_chunks(file_size: int) -> int:
    """Рассчитать количество частей для файла"""
    if file_size <= CHUNK_SIZE:
        return 1
    return (file_size + CHUNK_SIZE - 1) // CHUNK_SIZE


async def read_chunks(
    fp: BinaryIO, chunk_size: int = CHUNK_SIZE
) -> AsyncGenerator[bytes, None]:
    """
    Асинхронно читать файл порциями.
    """
    while True:
        chunk = fp.read(chunk_size)
        if not chunk:
            break
        yield chunk


async def read_chunks_from_stream(
    file_stream: io.BytesIO,
    file_size: int
) -> AsyncGenerator[Tuple[int, bytes], None]:
    """
    Прочитать файл из потока и разделить на части.
    
    Args:
        file_stream: BytesIO объект с содержимым файла
        file_size: Размер файла
    
    Yields:
        Кортеж (номер_части, данные_части)
    """
    file_stream.seek(0)
    chunk_number = 0
    bytes_read = 0
    
    while bytes_read < file_size:
        # Определяем размер текущей части
        remaining = file_size - bytes_read
        current_chunk_size = min(CHUNK_SIZE, remaining)
        
        # Читаем данные
        chunk_data = file_stream.read(current_chunk_size)
        if not chunk_data:
            break
        
        bytes_read += len(chunk_data)
        yield chunk_number, chunk_data
        chunk_number += 1


async def stream_file_chunks(
    chunks_data: List[bytes]
) -> AsyncGenerator[bytes, None]:
    """
    Потоково отправить части файла как единый файл.
    
    Args:
        chunks_data: Список с данными всех частей
    
    Yields:
        Блоки данных для отправки клиенту
    """
    for chunk in chunks_data:
        yield chunk


def get_chunk_info(file_size: int) -> dict:
    """
    Получить информацию о разделении файла на части.
    
    Args:
        file_size: Размер файла
    
    Returns:
        Dict с информацией о чанках
    """
    chunk_count = calculate_chunks(file_size)
    chunks_info = []
    
    bytes_processed = 0
    for i in range(chunk_count):
        remaining = file_size - bytes_processed
        current_size = min(CHUNK_SIZE, remaining)
        
        chunks_info.append({
            'number': i,
            'size': current_size,
            'offset': bytes_processed,
        })
        bytes_processed += current_size
    
    return {
        'total_chunks': chunk_count,
        'file_size': file_size,
        'chunks': chunks_info
    }

