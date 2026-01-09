# TeleDAV

TeleDAV is a server application that uses a Telegram bot as a backend for file storage, accessible via the WebDAV protocol. It's designed to be used with clients like Nextcloud, allowing you to mount your Telegram group's "Topics" as a virtual file system.

## Features

- **Telegram as Storage**: Uses a Telegram group with "Topics" (Forums) as the underlying file storage.
- **WebDAV Interface**: Provides a WebDAV server for compatibility with clients like Nextcloud, Windows, macOS, etc.
- **Large File Splitting**: Automatically splits files larger than 49.9 MB into chunks for upload.
- **Folder Mapping**: Each WebDAV folder corresponds to a "Topic" in the Telegram group.
- **SQLite Metadata**: A local SQLite database stores metadata to map files and chunks to their respective Telegram messages.
- **Dockerized**: Comes with `Dockerfile` and `docker-compose.yml` for easy setup.

## How It Works

- **MKCOL (Create Directory)**: Creates a new Topic in the Telegram group.
- **PUT (Upload File)**: Splits the file into chunks if necessary and uploads them as documents into the corresponding Topic.
- **DELETE (Directory)**: Deletes the corresponding Topic in Telegram, removing all messages within it.
- **DELETE (File)**: Deletes all Telegram messages (chunks) associated with the file.
- **PROPFIND / GET (List/Download)**: Lists files and folders by querying the local SQLite database.

**Note**: At the moment, downloading files (`GET`) is **not implemented**. The provider logic for re-assembling chunks and streaming them back to the client is a complex task and is left as a placeholder.

## Prerequisites

1.  A Telegram Bot Token. Talk to [@BotFather](https://t.me/BotFather) to create one.
2.  A Telegram group with "Topics" enabled where your bot is an administrator.
3.  The Chat ID of your Telegram group.
4.  Docker and Docker Compose installed.

## How to Run

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/Sppqq/TeleDAV.git
    cd TeleDAV
    ```

2.  **Configure your environment:**
    -   Create a `.env` file by copying the example: `cp .env.example .env`
    -   Edit the `.env` file with your details:

    ```env
    # Telegram Bot Configuration
    BOT_TOKEN=your_telegram_bot_token
    CHAT_ID=your_telegram_chat_id # This should be a negative number for groups

    # WebDAV Server Configuration
    DAV_USERNAME=admin
    DAV_PASSWORD=password
    DAV_HOST=0.0.0.0
    DAV_PORT=8080

    # Database Configuration
    DATABASE_URL=sqlite+aiosqlite:///teledav.db
    ```

3.  **Run with Docker Compose:**
    ```bash
    docker-compose up --build
    ```

4.  **Connect via WebDAV:**
    -   Your WebDAV server will be available at `http://localhost:8080`.
    -   Use the `DAV_USERNAME` and `DAV_PASSWORD` from your `.env` file to authenticate.

## Connecting to Nextcloud

1.  In Nextcloud, go to "Settings" -> "External storages".
2.  Add a new storage:
    -   **Folder name**: Whatever you like (e.g., `Telegram`)
    -   **External storage**: WebDAV
    -   **Authentication**: Username and password
    -   **URL**: `http://<your_server_ip>:8080/`
    -   **Username**: The `DAV_USERNAME` from your `.env` file.
    -   **Password**: The `DAV_PASSWORD` from your `.env` file.
3.  Click the checkmark to save. A green check should appear if the connection is successful.

## Limitations and Future Work

-   **File download is not implemented.** The `get_resource_data` method in the WebDAV provider needs to be built to fetch file chunks from Telegram and stream them back.
-   **Parallel Uploads**: While the architecture supports it, the current implementation uploads chunks sequentially within a single `create_resource` call.
-   **Error Handling**: The error handling is basic and could be improved to be more robust, especially for failed uploads.
-   **Performance**: The recursive delete and frequent database calls could be optimized for better performance on large-scale operations.
