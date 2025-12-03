#!/bin/bash
# entrypoint.sh

# --- 1. АКТУАЛЬНЫЙ ПАРСИНГ DATABASE_URL ---
# URL имеет вид: postgresql+asyncpg://user:pass@host:port/dbname
# Извлекаем часть URL после @
HOST_PORT_PATH=$(echo "$DATABASE_URL" | sed -e 's/.*@//')

# Извлекаем хост и порт, убирая путь (path) и порт, если они есть
DB_HOST=$(echo "$HOST_PORT_PATH" | sed -e 's/:.*//' -e 's/\/.*//')

# Извлекаем порт (часть между : и /)
DB_PORT=$(echo "$HOST_PORT_PATH" | sed -e 's/.*://' -e 's/\/.*//')

# Устанавливаем дефолт: 5432, если порт не был найден (что маловероятно для Supabase/Render)
if [ -z "$DB_PORT" ]; then
    DB_PORT=5432
fi

echo "--- Connection Details ---"
echo "DATABASE_URL environment variable is set."
echo "DB Host: $DB_HOST"
echo "DB Port: $DB_PORT"
echo "--------------------------"


# 2. Ждем, пока база данных станет доступна
# Используем извлеченные переменные.
echo "Waiting for database connection at $DB_HOST:$DB_PORT..."
until nc -z -v -w30 "$DB_HOST" "$DB_PORT"
do
  echo "Database connection failed. Retrying in 5 seconds..."
  sleep 5
done
echo "Database is ready."

# 3. Запускаем миграции Alembic
echo "Applying database migrations..."
# Alembic увидит переменную DATABASE_URL и подключится через нее
alembic upgrade head

# 4. Запускаем основное приложение (Web Service)
echo "Starting Uvicorn web server..."
# exec - гарантирует, что Uvicorn будет основным процессом (PID 1)
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4