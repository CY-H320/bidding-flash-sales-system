#!/bin/bash

# Bidding Flash Sale System - Startup Script

echo "🚀 Starting Bidding Flash Sale System Backend..."
echo ""

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "❌ Virtual environment not found. Please create one first:"
    echo "   python -m venv .venv"
    echo "   source .venv/bin/activate"
    echo "   pip install -r requirements.txt"
    exit 1
fi

# Activate virtual environment
source .venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "⚠️  .env file not found. Creating from .env.example..."
    cp .env.example .env
    echo "✅ Created .env file. Please update it with your settings."
fi

# Check PostgreSQL connection
echo "📊 Checking PostgreSQL connection..."
if command -v pg_isready &> /dev/null; then
    if pg_isready -h localhost -p 5432 &> /dev/null; then
        echo "✅ PostgreSQL is running"
    else
        echo "⚠️  PostgreSQL not responding. Make sure it's running:"
        echo "   docker-compose up -d db"
        echo "   OR"
        echo "   brew services start postgresql@15"
    fi
else
    echo "⚠️  pg_isready not found. Skipping PostgreSQL check."
fi

# Check Redis connection
echo "🔴 Checking Redis connection..."
if command -v redis-cli &> /dev/null; then
    if redis-cli ping &> /dev/null; then
        echo "✅ Redis is running"
    else
        echo "⚠️  Redis not responding. Make sure it's running:"
        echo "   docker-compose up -d redis"
        echo "   OR"
        echo "   brew services start redis"
    fi
else
    echo "⚠️  redis-cli not found. Skipping Redis check."
fi

echo ""
echo "🌟 Starting FastAPI server..."
echo "   API: http://localhost:8000"
echo "   Docs: http://localhost:8000/docs"
echo ""

# Run the server
python -m app.main
