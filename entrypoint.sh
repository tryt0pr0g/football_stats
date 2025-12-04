#!/bin/bash
set -e

DB_HOST=$(python3 -c "import urllib.parse, os; print(urllib.parse.urlparse(os.environ['DATABASE_URL']).hostname)")
DB_PORT=$(python3 -c "import urllib.parse, os; print(urllib.parse.urlparse(os.environ['DATABASE_URL']).port or 5432)")

echo "Waiting for database connection at $DB_HOST:$DB_PORT..."
until nc -z -v -w30 "$DB_HOST" "$DB_PORT"
do
  echo "Database connection failed. Retrying in 5 seconds..."
  sleep 5
done
echo "Database is ready."

echo "Applying database migrations..."
alembic upgrade head

echo "Starting Uvicorn web server..."
exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers 4