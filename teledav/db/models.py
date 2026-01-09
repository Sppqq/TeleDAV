import datetime
from sqlalchemy import (
    create_engine,
    Column,
    Integer,
    String,
    Boolean,
    BigInteger,
    DateTime,
    ForeignKey,
    UniqueConstraint,
    Text,
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from teledav.config import settings

Base = declarative_base()


class User(Base):
    """Модель пользователя"""
    __tablename__ = "users"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String(255), unique=True, index=True, nullable=False)
    email = Column(String(255), unique=True, index=True, nullable=True)
    password_hash = Column(String(255), nullable=False)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)


class Folder(Base):
    """Модель папки (Topic в Telegram)"""
    __tablename__ = "folders"

    id = Column(Integer, primary_key=True, index=True)
    name = Column(String(255), nullable=False, unique=True)
    path = Column(String(1024), unique=True, index=True, nullable=False)
    topic_id = Column(BigInteger, nullable=True)  # Telegram Topic ID
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    files = relationship("File", back_populates="folder", cascade="all, delete-orphan")
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    user = relationship("User")


class File(Base):
    """Модель файла"""
    __tablename__ = "files"

    id = Column(Integer, primary_key=True, index=True)
    folder_id = Column(Integer, ForeignKey("folders.id"), nullable=False)
    user_id = Column(Integer, ForeignKey("users.id"), nullable=False)
    name = Column(String(255), nullable=False)
    path = Column(String(1024), unique=True, index=True, nullable=False)
    size = Column(BigInteger, nullable=False)  # Общий размер файла
    mime_type = Column(String(100), default="application/octet-stream")
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)

    # Relationships
    folder = relationship("Folder", back_populates="files")
    user = relationship("User")
    chunks = relationship("FileChunk", back_populates="file", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("path", name="uq_file_path"),)


class FileChunk(Base):
    """Модель части файла"""
    __tablename__ = "file_chunks"

    id = Column(Integer, primary_key=True, index=True)
    file_id = Column(Integer, ForeignKey("files.id"), nullable=False)
    chunk_number = Column(Integer, nullable=False)  # Порядковый номер части
    size = Column(BigInteger, nullable=False)  # Размер этой части
    message_id = Column(BigInteger, nullable=True)  # Telegram Message ID
    thread_id = Column(BigInteger, nullable=True)  # Telegram Thread ID (Topic)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)

    # Relationships
    file = relationship("File", back_populates="chunks")


engine = create_async_engine(settings.database_url)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
