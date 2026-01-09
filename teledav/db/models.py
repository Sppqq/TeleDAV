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
)
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship, sessionmaker
from sqlalchemy.ext.asyncio import create_async_engine, AsyncSession

from teledav.config import settings

Base = declarative_base()


class FileSystemNode(Base):
    __tablename__ = "fs_nodes"

    id = Column(Integer, primary_key=True)
    path = Column(String, unique=True, index=True, nullable=False)
    parent_path = Column(String, index=True, nullable=False)
    name = Column(String, nullable=False)
    is_collection = Column(Boolean, default=False)
    size = Column(BigInteger, default=0)
    created_at = Column(DateTime, default=datetime.datetime.utcnow)
    modified_at = Column(DateTime, default=datetime.datetime.utcnow, onupdate=datetime.datetime.utcnow)
    telegram_topic_id = Column(BigInteger, nullable=True)

    chunks = relationship("FileChunk", back_populates="node", cascade="all, delete-orphan")

    __table_args__ = (UniqueConstraint("path", name="uq_path"),)

    def is_dir(self):
        return self.is_collection

    def get_display_name(self):
        return self.name


class FileChunk(Base):
    __tablename__ = "file_chunks"

    id = Column(Integer, primary_key=True)
    node_id = Column(Integer, ForeignKey("fs_nodes.id"), nullable=False)
    telegram_message_id = Column(BigInteger, nullable=False)
    telegram_file_id = Column(String, nullable=False)
    chunk_order = Column(Integer, nullable=False)

    node = relationship("FileSystemNode", back_populates="chunks")


engine = create_async_engine(settings.database_url)
AsyncSessionLocal = sessionmaker(engine, class_=AsyncSession, expire_on_commit=False)


async def get_db():
    async with AsyncSessionLocal() as session:
        yield session


async def create_tables():
    async with engine.begin() as conn:
        await conn.run_sync(Base.metadata.create_all)
