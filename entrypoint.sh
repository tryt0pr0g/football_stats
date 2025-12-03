#!/bin/bash
# entrypoint.sh

# --- 1. ИЗВЛЕЧЕНИЕ ХОСТА И ПОРТА ИЗ DATABASE_URL ---
# Используем URL-парсер, чтобы безопасно извлечь хост и порт.
# Render часто использует внутренние URL типа: postgres-instance.internal
DB_HOST=$(python3 -c "import urllib.parse, os; print(urllib.parse.urlparse(os.environ['DATABASE_URL']).hostname)")
DB_PORT=$(python3 -c "import urllib.parse, os; print(urllib.parse.urlparse(os.environ['DATABASE_URL']).port)")

# Убедимся, что порт установлен (по умолчанию 5432)
DB_PORT=${DB_PORT:-5432}

# 2. Ждем, пока база данных станет доступна
echo "Waiting for database connection at $DB_HOST:$DB_PORT..."
until nc -z -v -w30 $DB_HOST $DB_PORT
do
  echo "Database connection failed. Retrying in 5 seconds..."
  sleep 5
done
echo "Database is ready."

# 3. Запускаем миграции Alembic
echo "Applying database migrations..."
# ENTRYPOINT всегда должен использовать ENTRYPOINT ["/bin/bash", "-c", "..."]
# или exec, чтобы запустить основной процесс с PID 1.
alembic upgrade head

# 4. Запускаем основное приложение (Web Service)
echo "Starting Uvicorn web server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4