# 競標秒殺系統後端 (Bidding Flash Sale System Backend)

基於 FastAPI、PostgreSQL 和 Redis 的高效能競標秒殺系統。

## 🚀 功能特色

- ⚡ **高效能非同步架構** - 使用 FastAPI + asyncio
- 🗄️ **PostgreSQL 資料庫** - 使用 SQLAlchemy 2.0 ORM
- 🔥 **Redis 快取** - 庫存管理和排名系統
- 🔐 **JWT 認證** - 安全的使用者認證
- 📊 **即時競標排名** - Redis Sorted Set 實現
- 🐰 **訊息佇列** - RabbitMQ 處理非同步任務

## 📋 系統需求

- Python 3.12+
- PostgreSQL 15+
- Redis 7+
- RabbitMQ 3.12+

## 🛠️ 安裝步驟

### 1. 克隆專案

```bash
git clone <repository-url>
cd bidding-flash-sale-system-backend
```

### 2. 安裝依賴

使用 uv (推薦):
```bash
uv sync
```

或使用 pip:
```bash
pip install -r requirements.txt
```

### 3. 設定環境變數

```bash
cp .env.example .env
```

編輯 `.env` 檔案，修改必要的配置。

### 4. 啟動資料庫服務

使用 Docker Compose:
```bash
docker-compose up -d
```

### 5. 執行資料庫遷移

```bash
# 建立初始遷移
alembic revision --autogenerate -m "Initial migration"

# 執行遷移
alembic upgrade head
```

### 6. 啟動應用程式

```bash
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

## 📁 專案結構

```
bidding-flash-sale-system-backend/
├── alembic/                    # 資料庫遷移檔案
│   ├── versions/              # 遷移版本
│   ├── env.py                 # Alembic 環境配置
│   └── script.py.mako         # 遷移腳本模板
├── app/
│   ├── api/                   # API 路由
│   ├── core/                  # 核心配置
│   │   ├── config.py         # 應用程式配置
│   │   ├── database.py       # 資料庫連接
│   │   └── redis.py          # Redis 連接
│   ├── db/                    # 資料庫模型
│   │   └── models.py         # SQLAlchemy 模型
│   ├── models/                # Pydantic 模型
│   │   ├── user.py
│   │   ├── product.py
│   │   └── bid.py
│   ├── schemas/               # API Schemas
│   ├── services/              # 業務邏輯
│   ├── tasks/                 # 背景任務
│   ├── websockets/            # WebSocket 處理
│   └── main.py               # 應用程式入口
├── .env.example               # 環境變數範例
├── alembic.ini               # Alembic 配置
├── docker-compose.yml        # Docker 服務配置
├── pyproject.toml            # 專案配置
└── README.md                 # 說明文件
```

## 🔧 資料庫模型

### User (使用者)
- id (UUID)
- username (字串)
- email (字串)
- password (雜湊)
- is_admin (布林)

### BiddingProduct (競標商品)
- id (UUID)
- name (字串)
- description (字串)
- admin_id (UUID)

### BiddingSession (競標場次)
- id (UUID)
- product_id (UUID)
- upset_price (浮點數) - 起標價
- final_price (浮點數) - 最終成交價
- inventory (整數) - 庫存
- alpha, beta, gamma (浮點數) - 競標參數
- start_time, end_time (日期時間)
- duration (時間間隔)

### BiddingSessionRanking (競標排名)
- id (UUID)
- session_id (UUID)
- user_id (UUID)
- ranking (整數)
- bid_price (浮點數)
- bid_score (浮點數)
- is_winner (布林)

## 🌐 API 端點

### 健康檢查
- `GET /` - 基本健康檢查
- `GET /health` - 詳細健康檢查（包含資料庫和 Redis 狀態）

## 🔐 環境變數說明

| 變數名稱 | 說明 | 預設值 |
|---------|------|--------|
| `APP_NAME` | 應用程式名稱 | Bidding Flash Sale System |
| `DEBUG` | 除錯模式 | False |
| `POSTGRES_HOST` | PostgreSQL 主機 | localhost |
| `POSTGRES_PORT` | PostgreSQL 埠號 | 5432 |
| `POSTGRES_DB` | 資料庫名稱 | bidding-flash-sale-system |
| `REDIS_HOST` | Redis 主機 | localhost |
| `REDIS_PORT` | Redis 埠號 | 6379 |
| `SECRET_KEY` | JWT 密鑰 | (請務必修改) |

## 📝 開發指令

```bash
# 啟動開發伺服器
uvicorn app.main:app --reload

# 建立新的資料庫遷移
alembic revision --autogenerate -m "描述"

# 執行遷移
alembic upgrade head

# 回滾遷移
alembic downgrade -1

# 查看遷移歷史
alembic history

# 執行測試
pytest

# 程式碼格式化
ruff format .

# 程式碼檢查
ruff check .
```

## 🐳 Docker 使用

```bash
# 啟動所有服務
docker-compose up -d

# 查看日誌
docker-compose logs -f

# 停止服務
docker-compose down

# 清除所有資料
docker-compose down -v
```