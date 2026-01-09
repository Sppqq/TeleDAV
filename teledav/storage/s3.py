"""
S3 хранилище для файлов
Поддерживает AWS S3, MinIO и другие S3-совместимые сервисы
"""
import boto3
import logging
from io import BytesIO
from typing import Optional
from teledav.config import settings

logger = logging.getLogger(__name__)


class S3Storage:
    """Работа с S3 хранилищем"""
    
    def __init__(self):
        self.enabled = settings.s3_enabled
        self.bucket = settings.s3_bucket
        
        if not self.enabled:
            return
        
        # Инициализируем S3 клиент
        s3_config = {
            'aws_access_key_id': settings.s3_access_key,
            'aws_secret_access_key': settings.s3_secret_key,
            'region_name': settings.s3_region,
        }
        
        # Если используется MinIO или другой S3-совместимый сервис
        if settings.s3_endpoint_url:
            s3_config['endpoint_url'] = settings.s3_endpoint_url
        
        self.client = boto3.client('s3', **s3_config)
        
        # Проверяем доступ и создаём bucket если нужно
        try:
            self.client.head_bucket(Bucket=self.bucket)
            logger.info(f"✅ S3 bucket '{self.bucket}' accessible")
        except Exception as e:
            logger.warning(f"S3 bucket '{self.bucket}' not accessible: {e}")
    
    async def upload(self, file_key: str, content: bytes) -> bool:
        """Загрузить файл в S3"""
        if not self.enabled:
            return False
        
        try:
            self.client.put_object(
                Bucket=self.bucket,
                Key=file_key,
                Body=content
            )
            logger.info(f"✅ Uploaded {file_key} to S3")
            return True
        except Exception as e:
            logger.error(f"❌ S3 upload error: {e}")
            return False
    
    async def download(self, file_key: str) -> Optional[bytes]:
        """Скачать файл из S3"""
        if not self.enabled:
            return None
        
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=file_key)
            content = response['Body'].read()
            logger.info(f"✅ Downloaded {file_key} from S3")
            return content
        except Exception as e:
            logger.error(f"❌ S3 download error: {e}")
            return None
    
    async def delete(self, file_key: str) -> bool:
        """Удалить файл из S3"""
        if not self.enabled:
            return False
        
        try:
            self.client.delete_object(Bucket=self.bucket, Key=file_key)
            logger.info(f"✅ Deleted {file_key} from S3")
            return True
        except Exception as e:
            logger.error(f"❌ S3 delete error: {e}")
            return False


# Глобальный экземпляр
s3_storage = S3Storage()
