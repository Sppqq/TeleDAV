"""
FastAPI приложение для TeleDAV.
Полноценный REST API с веб интерфейсом, аутентификацией и S3 поддержкой.
"""
import logging
from fastapi import FastAPI, HTTPException, Depends, UploadFile, File, Form, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import List, Optional
import jwt
import hashlib
from datetime import datetime, timedelta

from teledav.config import settings
from teledav.db.models import create_tables, AsyncSessionLocal, User
from teledav.db.service import DatabaseService
from teledav.storage.s3 import s3_storage

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
    description="Telegram-powered file storage with web UI and S3",
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
        
        if s3_storage.enabled:
            logger.info("✅ S3 storage enabled")
        else:
            logger.info("⚠️  S3 storage disabled - using Telegram")
    except Exception as e:
        logger.error(f"❌ Error initializing: {e}")


@app.on_event("shutdown")
async def shutdown_event():
    """Очистка при остановке"""
    logger.info("Shutting down TeleDAV server...")


@app.get("/health")
async def health_check():
    """Проверка здоровья приложения"""
    return {
        "status": "ok",
        "service": "TeleDAV",
        "s3_enabled": s3_storage.enabled
    }


# ============ WEB INTERFACE ============

@app.get("/app", response_class=HTMLResponse)
async def web_app():
    """Веб приложение - SPA"""
    return """<!DOCTYPE html>
<html lang="ru">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TeleDAV - File Storage</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, sans-serif;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            display: flex;
            align-items: center;
            justify-content: center;
        }
        
        .container {
            background: white;
            border-radius: 10px;
            box-shadow: 0 10px 40px rgba(0,0,0,0.2);
            width: 100%;
            max-width: 500px;
            padding: 40px;
        }
        
        .logo {
            text-align: center;
            margin-bottom: 30px;
            font-size: 32px;
            font-weight: bold;
            color: #667eea;
        }
        
        .form-group {
            margin-bottom: 20px;
        }
        
        label {
            display: block;
            margin-bottom: 8px;
            color: #333;
            font-weight: 500;
        }
        
        input[type="text"],
        input[type="password"],
        input[type="email"] {
            width: 100%;
            padding: 12px;
            border: 2px solid #e0e0e0;
            border-radius: 5px;
            font-size: 14px;
            transition: border-color 0.3s;
        }
        
        input:focus {
            outline: none;
            border-color: #667eea;
        }
        
        button {
            width: 100%;
            padding: 12px;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            color: white;
            border: none;
            border-radius: 5px;
            font-size: 16px;
            font-weight: 600;
            cursor: pointer;
            transition: transform 0.2s;
        }
        
        button:hover {
            transform: translateY(-2px);
        }
        
        .toggle-form {
            text-align: center;
            margin-top: 20px;
            color: #666;
        }
        
        .toggle-form a {
            color: #667eea;
            cursor: pointer;
            text-decoration: none;
            font-weight: 600;
        }
        
        .error {
            background: #fee;
            color: #c00;
            padding: 12px;
            border-radius: 5px;
            margin-bottom: 20px;
            display: none;
        }
        
        .success {
            background: #efe;
            color: #0a0;
            padding: 12px;
            border-radius: 5px;
            margin-bottom: 20px;
            display: none;
        }
        
        .dashboard {
            display: none;
        }
        
        .dashboard.active {
            display: block;
        }
        
        .auth-forms {
            display: block;
        }
        
        .auth-forms.hidden {
            display: none;
        }
        
        .header {
            display: flex;
            justify-content: space-between;
            align-items: center;
            margin-bottom: 30px;
        }
        
        .logout-btn {
            width: auto;
            padding: 8px 16px;
            font-size: 14px;
        }
        
        .file-upload {
            border: 2px dashed #667eea;
            padding: 20px;
            text-align: center;
            border-radius: 5px;
            margin-bottom: 20px;
            cursor: pointer;
            transition: background 0.3s;
        }
        
        .file-upload:hover {
            background: #f5f5f5;
        }
        
        .files-list {
            margin-top: 20px;
        }
        
        .file-item {
            display: flex;
            justify-content: space-between;
            align-items: center;
            padding: 15px;
            background: #f9f9f9;
            border-radius: 5px;
            margin-bottom: 10px;
        }
        
        .file-info {
            flex: 1;
        }
        
        .file-name {
            font-weight: 600;
            color: #333;
        }
        
        .file-size {
            font-size: 12px;
            color: #999;
        }
        
        .file-actions {
            display: flex;
            gap: 10px;
        }
        
        .btn-small {
            padding: 6px 12px;
            font-size: 12px;
            width: auto;
            background: #667eea;
            color: white;
            border: none;
            border-radius: 3px;
            cursor: pointer;
        }
        
        .btn-small.delete {
            background: #e74c3c;
        }
        
        input[type="file"] {
            display: none;
        }
    </style>
</head>
<body>
    <div class="container">
        <div class="auth-forms">
            <div class="logo">📦 TeleDAV</div>
            
            <div id="login-form">
                <h2 style="margin-bottom: 20px; color: #333;">Login</h2>
                <div class="error" id="login-error"></div>
                <div class="form-group">
                    <label>Username</label>
                    <input type="text" id="login-username" placeholder="Enter username">
                </div>
                <div class="form-group">
                    <label>Password</label>
                    <input type="password" id="login-password" placeholder="Enter password">
                </div>
                <button onclick="login()">Login</button>
                <div class="toggle-form">
                    Don't have account? <a onclick="toggleForms()">Register</a>
                </div>
            </div>
            
            <div id="register-form" style="display: none;">
                <h2 style="margin-bottom: 20px; color: #333;">Register</h2>
                <div class="error" id="register-error"></div>
                <div class="form-group">
                    <label>Username</label>
                    <input type="text" id="register-username" placeholder="Choose username">
                </div>
                <div class="form-group">
                    <label>Email (optional)</label>
                    <input type="email" id="register-email" placeholder="Enter email">
                </div>
                <div class="form-group">
                    <label>Password</label>
                    <input type="password" id="register-password" placeholder="Enter password">
                </div>
                <button onclick="register()">Register</button>
                <div class="toggle-form">
                    Already have account? <a onclick="toggleForms()">Login</a>
                </div>
            </div>
        </div>
        
        <div class="dashboard">
            <div class="header">
                <h2 style="color: #333;">My Files</h2>
                <button class="logout-btn" onclick="logout()">Logout</button>
            </div>
            
            <div class="success" id="upload-success"></div>
            <div class="error" id="upload-error"></div>
            
            <div class="file-upload" onclick="document.getElementById('file-input').click()">
                <div style="font-size: 40px;">📁</div>
                <div style="color: #667eea; font-weight: 600;">Click or drag files here</div>
            </div>
            <input type="file" id="file-input" onchange="uploadFile()">
            
            <div class="files-list" id="files-list">
                <p style="color: #999; text-align: center;">No files yet</p>
            </div>
        </div>
    </div>
    
    <script>
        const API_URL = '/api';
        let token = localStorage.getItem('token');
        
        function toggleForms() {
            document.getElementById('login-form').style.display = 
                document.getElementById('login-form').style.display === 'none' ? 'block' : 'none';
            document.getElementById('register-form').style.display = 
                document.getElementById('register-form').style.display === 'none' ? 'block' : 'none';
        }
        
        async function register() {
            const username = document.getElementById('register-username').value;
            const email = document.getElementById('register-email').value;
            const password = document.getElementById('register-password').value;
            const errorDiv = document.getElementById('register-error');
            
            try {
                const res = await fetch(API_URL + '/auth/register', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, email, password })
                });
                
                if (!res.ok) {
                    const data = await res.json();
                    throw new Error(data.detail || 'Registration failed');
                }
                
                const data = await res.json();
                localStorage.setItem('token', data.access_token);
                showDashboard();
            } catch (err) {
                errorDiv.textContent = err.message;
                errorDiv.style.display = 'block';
            }
        }
        
        async function login() {
            const username = document.getElementById('login-username').value;
            const password = document.getElementById('login-password').value;
            const errorDiv = document.getElementById('login-error');
            
            try {
                const res = await fetch(API_URL + '/auth/login', {
                    method: 'POST',
                    headers: { 'Content-Type': 'application/json' },
                    body: JSON.stringify({ username, password })
                });
                
                if (!res.ok) {
                    throw new Error('Invalid credentials');
                }
                
                const data = await res.json();
                localStorage.setItem('token', data.access_token);
                showDashboard();
            } catch (err) {
                errorDiv.textContent = err.message;
                errorDiv.style.display = 'block';
            }
        }
        
        async function uploadFile() {
            const fileInput = document.getElementById('file-input');
            const file = fileInput.files[0];
            const errorDiv = document.getElementById('upload-error');
            const successDiv = document.getElementById('upload-success');
            
            if (!file) return;
            
            const formData = new FormData();
            formData.append('file', file);
            
            try {
                const res = await fetch(API_URL + '/files/upload', {
                    method: 'POST',
                    headers: { 'Authorization': 'Bearer ' + token },
                    body: formData
                });
                
                if (!res.ok) throw new Error('Upload failed');
                
                successDiv.textContent = 'File uploaded successfully!';
                successDiv.style.display = 'block';
                fileInput.value = '';
                loadFiles();
                
                setTimeout(() => successDiv.style.display = 'none', 3000);
            } catch (err) {
                errorDiv.textContent = err.message;
                errorDiv.style.display = 'block';
            }
        }
        
        async function loadFiles() {
            try {
                const res = await fetch(API_URL + '/files', {
                    headers: { 'Authorization': 'Bearer ' + token }
                });
                
                if (!res.ok) throw new Error('Failed to load files');
                
                const files = await res.json();
                const list = document.getElementById('files-list');
                
                if (files.length === 0) {
                    list.innerHTML = '<p style="color: #999; text-align: center;">No files yet</p>';
                    return;
                }
                
                list.innerHTML = files.map(f => `
                    <div class="file-item">
                        <div class="file-info">
                            <div class="file-name">${f.name}</div>
                            <div class="file-size">${(f.size / 1024).toFixed(2)} KB</div>
                        </div>
                        <div class="file-actions">
                            <button class="btn-small delete" onclick="deleteFile(${f.id})">Delete</button>
                        </div>
                    </div>
                `).join('');
            } catch (err) {
                console.error(err);
            }
        }
        
        async function deleteFile(id) {
            if (!confirm('Delete this file?')) return;
            
            try {
                const res = await fetch(API_URL + '/files/' + id, {
                    method: 'DELETE',
                    headers: { 'Authorization': 'Bearer ' + token }
                });
                
                if (!res.ok) throw new Error('Delete failed');
                
                loadFiles();
            } catch (err) {
                alert(err.message);
            }
        }
        
        function showDashboard() {
            document.querySelector('.auth-forms').style.display = 'none';
            document.querySelector('.dashboard').style.display = 'block';
            loadFiles();
        }
        
        function logout() {
            localStorage.removeItem('token');
            token = null;
            document.querySelector('.auth-forms').style.display = 'block';
            document.querySelector('.dashboard').style.display = 'none';
            document.getElementById('login-form').style.display = 'block';
            document.getElementById('register-form').style.display = 'none';
        }
        
        if (token) {
            showDashboard();
        }
    </script>
</body>
</html>"""


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "TeleDAV - Telegram-powered file storage",
        "version": "1.0.0",
        "web_app": "/app",
        "docs": "/docs",
        "api": {
            "auth": ["/api/auth/register (POST)", "/api/auth/login (POST)"],
            "files": ["/api/files (GET)", "/api/files/upload (POST)", "/api/files/{id} (GET, DELETE)"]
        }
    }


# ============ AUTH ENDPOINTS ============

@app.post("/api/auth/register", response_model=TokenResponse)
async def register(user_data: UserRegister):
    """Регистрация нового пользователя"""
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            session.query(User).filter(User.username == user_data.username)
        )
        if result.scalars().first():
            raise HTTPException(status_code=400, detail="Username already exists")
        
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
        
        content = await file.read()
        file_size = len(content)
        
        # Если S3 включен, сохраняем туда
        if s3_storage.enabled:
            file_key = f"{current_user['user_id']}/{file.filename}"
            success = await s3_storage.upload(file_key, content)
            if not success:
                raise HTTPException(status_code=500, detail="Failed to upload to S3")
        
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
            "storage": "s3" if s3_storage.enabled else "telegram",
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
        
        if s3_storage.enabled:
            file_key = f"{current_user['user_id']}/{file_obj.name}"
            await s3_storage.delete(file_key)
        
        await db_service.delete_file(file_id)
        return {"message": "File deleted successfully"}

