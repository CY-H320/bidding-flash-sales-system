#!/usr/bin/env bash
set -euo pipefail

export PYTHONPATH=${PYTHONPATH:-/app}

# Load environment file if present
if [ -f /app/.env ]; then
  echo "Loading environment variables from .env"
  set -o allexport
  # shellcheck disable=SC1091
  source /app/.env
  set +o allexport
fi

echo "Creating database if it doesn't exist..."
python << 'EOF'
import os
import psycopg2
from psycopg2 import sql

try:
    # Connect to default postgres database to create our database
    conn = psycopg2.connect(
        host=os.getenv('POSTGRES_HOST', 'localhost'),
        port=int(os.getenv('POSTGRES_PORT', 5432)),
        user=os.getenv('POSTGRES_USER', 'postgres'),
        password=os.getenv('POSTGRES_PASSWORD', ''),
        database='postgres'
    )
    conn.autocommit = True
    cur = conn.cursor()
    
    db_name = os.getenv('POSTGRES_DB', 'bidding_db')
    try:
        cur.execute(sql.SQL("CREATE DATABASE {}").format(sql.Identifier(db_name)))
        print(f"Database {db_name} created successfully")
    except psycopg2.errors.DuplicateDatabase:
        print(f"Database {db_name} already exists")
    
    cur.close()
    conn.close()
except Exception as e:
    print(f"Warning: Could not create database: {e}")
    print("Continuing anyway, database might already exist...")
EOF

echo "Running database migrations..."
alembic upgrade head

echo "Starting FastAPI with uvicorn"
exec uvicorn app.main:app \
  --host "${UVICORN_HOST:-0.0.0.0}" \
  --port "${UVICORN_PORT:-8000}" \
  --workers "${UVICORN_WORKERS:-4}"
