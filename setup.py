from setuptools import setup, find_packages

setup(
    name="teledav",
    version="1.0.0",
    description="WebDAV Server powered by Telegram",
    author="Sppqq",
    packages=find_packages(),
    python_requires=">=3.10",
    install_requires=[
        "fastapi==0.110.0",
        "uvicorn[standard]==0.27.1",
        "pydantic==2.5.3",
        "aiogram==3.4.1",
        "sqlalchemy==2.0.25",
        "aiosqlite==0.19.0",
        "wsgidav==4.2.0",
        "python-dotenv==1.0.0",
    ],
)
