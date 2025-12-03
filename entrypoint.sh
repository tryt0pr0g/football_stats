#!/bin/bash
# entrypoint.sh

# 1. Задаем название хоста БД (берется из DATABASE_URL)
DB_HOST=$(echo $DATABASE_URL | sed -e 's/.*@//' -e 's/:.*//')

# 2. Ждем, пока база данных станет доступна
# Это критически важно, т.к. приложение может запуститься быстрее, чем БД
echo "Waiting for database connection at $DB_HOST..."
until nc -z -v -w30 $DB_HOST 5432
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
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4