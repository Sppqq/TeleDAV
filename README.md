# 🌐 TeleDAV

**WebDAV Server powered by Telegram** 📱💾

[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue?style=flat-square&logo=python)](https://www.python.org/)
[![FastAPI](https://img.shields.io/badge/FastAPI-0.110.0-009688?style=flat-square&logo=fastapi)](https://fastapi.tiangolo.com/)
[![Aiogram](https://img.shields.io/badge/Aiogram-3.4.1-blue?style=flat-square&logo=telegram)](https://github.com/aiogram/aiogram)
[![License MIT](https://img.shields.io/badge/License-MIT-green?style=flat-square)](LICENSE)
[![Docker](https://img.shields.io/badge/Docker-Ready-2496ed?style=flat-square&logo=docker)](docker-compose.yml)
[![Status](https://img.shields.io/badge/Status-Active-success?style=flat-square)](#)

<div align="center">

### 🚀 Turn Telegram Into Cloud Storage

**Mount Telegram as a WebDAV drive on Nextcloud, Windows, macOS, Linux, and more!**

[📖 Quick Start](#-quick-start) • [📚 Docs](#-documentation) • [🔧 Setup](#%EF%B8%8F-configuration) • [💬 Support](#-support)

</div>

---

## ✨ Why TeleDAV?

| Feature | Description |
|---------|-------------|
| 📦 **Auto Chunking** | Files > 50MB split automatically (Telegram limit) |
| ⚡ **Parallel Uploads** | Multiple chunks upload simultaneously |
| 🏷️ **Folder Organization** | Each WebDAV folder = Telegram Topic |
| 🔐 **Secure** | Basic Auth + Private Telegram Group |
| 🌍 **Universal Access** | Works with any WebDAV client |
| 💾 **Lightweight** | SQLite database, zero external deps |
| 🐳 **Docker Ready** | Production deployment in one command |
| 🚀 **Async** | Full async/await architecture |

---

## 📊 Tech Stack

| Component | Technology | Version |
|-----------|-----------|---------|
| **Runtime** | Python | 3.10+ |
| **Web Framework** | FastAPI | 0.110.0 |
| **Telegram** | Aiogram | 3.4.1 |
| **WebDAV Server** | WsgiDAV | 4.2.0 |
| **Database ORM** | SQLAlchemy | 2.0.25 |
| **Database** | SQLite | Latest |
| **ASGI Server** | Uvicorn | 0.27.1 |

---

## 📚 Documentation

| Document | Purpose |
|----------|---------|
| [🚀 QUICKSTART.md](QUICKSTART.md) | 5-minute setup guide |
| [🔧 IMPLEMENTATION.md](IMPLEMENTATION.md) | Technical architecture |
| [📁 PROJECT_STRUCTURE.md](PROJECT_STRUCTURE.md) | Code organization |
| [✅ CHECKLIST.md](CHECKLIST.md) | Requirements verification |

---

## 🚀 Quick Start

### ⚡ Option 1: Docker (Recommended)

```bash
# Clone
git clone https://github.com/Sppqq/TeleDAV.git
cd TeleDAV

# Configure
cp .env.example .env
nano .env  # Edit with your BOT_TOKEN and CHAT_ID

# Run
docker compose up --build
```

### 🐍 Option 2: Local Python

```bash
# Clone
git clone https://github.com/Sppqq/TeleDAV.git
cd TeleDAV

# Environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install & Configure
pip install -r requirements.txt
cp .env.example .env
nano .env  # Edit with your settings

# Run
python -m teledav.main
```

---

## ⚙️ Configuration

Create a `.env` file based on `.env.example`:

```env
# Telegram Bot Configuration
BOT_TOKEN=123456789:ABCDefghIjklmnOPQrstuvwxyz
CHAT_ID=-1001234567890

# WebDAV Server Configuration
DAV_USERNAME=admin
DAV_PASSWORD=YourSecurePassword123
DAV_HOST=0.0.0.0
DAV_PORT=5555

# Database
DATABASE_URL=sqlite+aiosqlite:///teledav.db
```

### 🔑 Get Your Credentials

<details>
<summary><b>How to get BOT_TOKEN?</b></summary>

1. Open Telegram and find [@BotFather](https://t.me/BotFather)
2. Send `/newbot` command
3. Give it a name (e.g., "MyTeleDAVBot")
4. Copy the token

</details>

<details>
<summary><b>How to get CHAT_ID?</b></summary>

1. Create a private Telegram group
2. **IMPORTANT:** Enable "Topics" in group settings
3. Add the bot as an admin
4. Find [@getidsbot](https://t.me/getidsbot)
5. Forward it to your group
6. Copy the Chat ID (negative number)

</details>

---

## 🔗 WebDAV Client Setup

### 🍎 macOS / 🐧 Linux

```bash
sudo apt-get install davfs2
mkdir ~/teledav
sudo mount -t davfs http://localhost:5555/ ~/teledav
# Username: admin, Password: (from .env)
```

### 🪟 Windows

1. Open File Explorer
2. Right-click "This PC" → "Map network drive"
3. Folder: `http://localhost:5555/`
4. ✓ Connect using different credentials
5. Username: `admin` / Password: (from .env)

### ☁️ Nextcloud

1. Settings → External storages
2. Add WebDAV:
   - **URL:** `http://localhost:5555/`
   - **Username:** `admin`
   - **Password:** (from .env)
3. Click "Check connection"

---

## 📊 Architecture

```
┌─────────────────────────────────────────────┐
│   WebDAV Client (Nextcloud, Windows, etc)   │
└──────────────────┬──────────────────────────┘
                   │ HTTP/WebDAV
┌──────────────────▼──────────────────────────┐
│    FastAPI + WsgiDAV (Uvicorn)              │
│  • Basic Auth                               │
│  • PUT/GET/DELETE/MKCOL                     │
└──────────┬────────────────────────┬─────────┘
           │                        │
    ┌──────▼─────┐        ┌────────▼───────┐
    │  SQLite    │        │    Telegram    │
    │  Metadata  │        │   Bot API      │
    └────────────┘        └────────────────┘
```

---

## 🔄 How It Works

### File Upload (100 MB example)

```
File → Split into chunks (49.9 MB each)
  ├─ Part 1: 49.9 MB → Telegram Message
  ├─ Part 2: 49.9 MB → Telegram Message
  └─ Part 3: 0.2 MB  → Telegram Message
  
Metadata stored in SQLite for reassembly
```

### Telegram Organization

```
Group (Chat)
  ├─ 📌 Topic: "Documents"
  │   ├─ 📄 file1.pdf (chunks)
  │   └─ 📄 file2.docx
  └─ 📌 Topic: "Images"
      └─ 🖼️ photo.jpg (chunks)
```

---

## 💾 Examples

### Create a folder
```bash
mkdir ~/teledav/MyDocuments
# → Creates a Telegram Topic automatically
```

### Upload a file
```bash
cp large_file.zip ~/teledav/MyDocuments/
# → Auto-splits and uploads in parallel
```

### Sync with Nextcloud
1. Go to Nextcloud Settings
2. Add "Telegram" external storage
3. Use like a normal folder
4. Everything auto-syncs!

---

## 🔒 Security

- ✅ Basic Auth for WebDAV
- ✅ Credentials in `.env` (not in git)
- ✅ Private Telegram group required
- ✅ Bot isolated in your group
- ✅ Use HTTPS reverse proxy in production

---

## 🐛 Troubleshooting

| Issue | Solution |
|-------|----------|
| ❌ "Invalid credentials" | Check `DAV_USERNAME` and `DAV_PASSWORD` in `.env` |
| ❌ "Topic not created" | Ensure group has "Topics" enabled |
| ❌ "Connection refused" | Verify server is running on port 5555 |
| ❌ "Bot permission denied" | Check bot is admin in the group |
| ❌ "Database error" | Delete `teledav.db` and restart |

For more help, see [QUICKSTART.md](QUICKSTART.md)

---

## 📦 Project Structure

```
TeleDAV/
├── teledav/
│   ├── main.py              # Entry point
│   ├── config.py            # Settings
│   ├── db/
│   │   ├── models.py        # ORM models
│   │   └── service.py       # CRUD operations
│   ├── bot/
│   │   └── service.py       # Telegram integration
│   ├── webdav/
│   │   ├── provider.py      # WebDAV provider
│   │   └── app.py           # FastAPI app
│   └── utils/
│       └── chunking.py      # File splitting
├── docker-compose.yml
├── Dockerfile
├── requirements.txt
└── README.md
```

**Stats:** ~830 lines of code + 1500+ lines of docs

---

## 📋 Requirements

- **Python** 3.10+
- **Telegram Bot** (get from [@BotFather](https://t.me/BotFather))
- **Telegram Group** with "Topics" enabled
- **Docker** (optional)

---

## 📝 License

MIT License - Use freely for personal or commercial projects

[View full license →](LICENSE)

---

## 🙏 Support

- ⭐ Star the repository if you like it!
- 🐛 [Report issues](https://github.com/Sppqq/TeleDAV/issues)
- 💬 [Discussions](https://github.com/Sppqq/TeleDAV/discussions)
- 🔗 Share with friends!

---

<div align="center">

**Version:** 1.0.0 | **Status:** ✅ Production Ready

Made with ❤️ for cloud storage

</div>
