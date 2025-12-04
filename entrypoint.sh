#!/bin/bash
set -e # Останавливаем скрипт при ошибке

# --- 1. АКТУАЛЬНЫЙ ПАРСИНГ DATABASE_URL ---
# Используем Python для надежного извлечения хоста и порта из URI
# (например, postgresql+asyncpg://user:pass@host:5432/dbname)
DB_HOST=$(python3 -c "import urllib.parse, os; print(urllib.parse.urlparse(os.environ['DATABASE_URL']).hostname)")
DB_PORT=$(python3 -c "import urllib.parse, os; print(urllib.parse.urlparse(os.environ['DATABASE_URL']).port or 5432)")

# 2. Ждем, пока база данных станет доступна
# Это критически важно, чтобы Alembic не упал
echo "Waiting for database connection at $DB_HOST:$DB_PORT..."
# nc (netcat) - проверяет доступность порта. Ждем 30 секунд.
until nc -z -v -w30 "$DB_HOST" "$DB_PORT"
do
  echo "Database connection failed. Retrying in 5 seconds..."
  sleep 5
done
echo "Database is ready."

# 3. Запускаем миграции Alembic
echo "Applying database migrations..."
alembic upgrade head

# 4. Запускаем основное приложение (Web Service)
echo "Starting Uvicorn web server..."
# exec - гарантирует, что Uvicorn будет основным процессом контейнера (PID 1)
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4