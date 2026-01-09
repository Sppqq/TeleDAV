"""
FastAPI приложение для TeleDAV.
Полноценный REST API с аутентификацией и управлением файлами.
"""
import logging
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from pydantic import BaseModel
from typing import List, Optional
import jwt
import hashlib
from datetime import datetime, timedelta

from teledav.config import settings
from teledav.db.models import create_tables, AsyncSessionLocal, User
from teledav.db.service import DatabaseService

logger = logging.getLogger(__name__)

JWT_SECRET = "teledav-secret-key-2024"
JWT_ALGORITHM = "HS256"


# ============ Pydantic Models ============

class UserRegister(BaseModel):
    username: str
    password: str
    email: Optional[str] = None


class UserLogin(BaseModel):
    username: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    token_type: str
    user_id: int
    username: str


class FileInfo(BaseModel):
    id: int
    name: str
    size: int
    mime_type: str
    created_at: datetime


# Создаем FastAPI приложение
app = FastAPI(
    title="TeleDAV",
    description="Telegram-powered file storage with REST API",
    version="1.0.0"
)

# Добавляем CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# ============ Helper Functions ============

def hash_password(password: str) -> str:
    """Хеширование пароля"""
    return hashlib.sha256(password.encode()).hexdigest()


def create_token(user_id: int, username: str) -> str:
    """Создание JWT токена"""
    payload = {
        "user_id": user_id,
        "username": username,
        "exp": datetime.utcnow() + timedelta(days=7)
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=JWT_ALGORITHM)


async def verify_token(token: str) -> dict:
    """Верификация JWT токена"""
    try:
        payload = jwt.decode(token, JWT_SECRET, algorithms=[JWT_ALGORITHM])
        return payload
    except jwt.InvalidTokenError:
        raise HTTPException(status_code=401, detail="Invalid token")


async def get_current_user(authorization: Optional[str] = Header(None)):
    """Получить текущего пользователя из токена"""
    if not authorization:
        raise HTTPException(status_code=401, detail="Not authenticated")
    
    try:
        scheme, token = authorization.split()
        if scheme.lower() != "bearer":
            raise HTTPException(status_code=401, detail="Invalid auth scheme")
        payload = await verify_token(token)
        return payload
    except ValueError:
        raise HTTPException(status_code=401, detail="Invalid token format")


@app.on_event("startup")
async def startup_event():
    """Инициализация при запуске"""
    logger.info("Starting TeleDAV server...")
    try:
        await create_tables()
        logger.info("✅ Database initialized successfully")
    except Exception as e:
        logger.error(f"❌ Error initializing database: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при остановке"""
    logger.info("Shutting down TeleDAV server...")


@app.get("/health")
async def health_check():
    """Проверка здоровья приложения"""
    return {"status": "ok", "service": "TeleDAV"}


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "TeleDAV - Telegram-powered file storage",
        "version": "1.0.0",
        "endpoints": {
            "auth": "/api/auth/register, /api/auth/login",
            "files": "/api/files (GET), /api/files/upload (POST), /api/files/{id} (GET, DELETE)",
            "docs": "/docs"
        }
    }


# ============ AUTH ENDPOINTS ============

@app.post("/api/auth/register", response_model=TokenResponse)
async def register(user_data: UserRegister):
    """Регистрация нового пользователя"""
    async with AsyncSessionLocal() as session:
        # Проверяем если пользователь уже существует
        result = await session.execute(
            session.query(User).filter(User.username == user_data.username)
        )
        if result.scalars().first():
            raise HTTPException(status_code=400, detail="Username already exists")
        
        # Создаём пользователя
        user = User(
            username=user_data.username,
            email=user_data.email or f"{user_data.username}@teledav.local",
            password_hash=hash_password(user_data.password)
        )
        session.add(user)
        await session.commit()
        await session.refresh(user)
        
        token = create_token(user.id, user.username)
        return {
            "access_token": token,
            "token_type": "bearer",
            "user_id": user.id,
            "username": user.username
        }


@app.post("/api/auth/login", response_model=TokenResponse)
async def login(user_data: UserLogin):
    """Логин пользователя"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            session.query(User).filter(User.username == user_data.username)
        )
        user = result.scalars().first()
        
        if not user or user.password_hash != hash_password(user_data.password):
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        token = create_token(user.id, user.username)
        return {
            "access_token": token,
            "token_type": "bearer",
            "user_id": user.id,
            "username": user.username
        }


# ============ FILE ENDPOINTS ============

@app.post("/api/files/upload")
async def upload_file(
    file: UploadFile = File(...),
    current_user: dict = Depends(get_current_user)
):
    """Загрузить файл"""
    async with AsyncSessionLocal() as session:
        db_service = DatabaseService(session)
        
        # Читаем файл в памяти
        content = await file.read()
        file_size = len(content)
        
        # Сохраняем файл
        file_obj = await db_service.create_file(
            folder_id=1,
            name=file.filename,
            path=f"/{file.filename}",
            size=file_size,
            mime_type=file.content_type or "application/octet-stream"
        )
        
        return {
            "id": file_obj.id,
            "name": file_obj.name,
            "size": file_obj.size,
            "path": file_obj.path,
            "message": "File uploaded successfully"
        }


@app.get("/api/files", response_model=List[FileInfo])
async def list_files(current_user: dict = Depends(get_current_user)):
    """Список файлов"""
    async with AsyncSessionLocal() as session:
        db_service = DatabaseService(session)
        
        files = await db_service.get_files_by_folder(1)
        return [
            FileInfo(
                id=f.id,
                name=f.name,
                size=f.size,
                mime_type=f.mime_type,
                created_at=f.created_at
            )
            for f in files
        ]


@app.get("/api/files/{file_id}")
async def get_file(file_id: int, current_user: dict = Depends(get_current_user)):
    """Информация о файле"""
    async with AsyncSessionLocal() as session:
        db_service = DatabaseService(session)
        
        file_obj = await db_service.get_file(file_id)
        if not file_obj:
            raise HTTPException(status_code=404, detail="File not found")
        
        return {
            "id": file_obj.id,
            "name": file_obj.name,
            "size": file_obj.size,
            "mime_type": file_obj.mime_type,
            "created_at": file_obj.created_at
        }


@app.delete("/api/files/{file_id}")
async def delete_file(file_id: int, current_user: dict = Depends(get_current_user)):
    """Удалить файл"""
    async with AsyncSessionLocal() as session:
        db_service = DatabaseService(session)
        
        file_obj = await db_service.get_file(file_id)
        if not file_obj:
            raise HTTPException(status_code=404, detail="File not found")
        
        await db_service.delete_file(file_id)
        return {"message": "File deleted successfully"}

