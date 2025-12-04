# Используем официальный образ Python с Alpine (легкий дистрибутив Linux)
FROM python:3.11-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Устанавливаем netcat (nc) для проверки доступности БД в entrypoint.sh
RUN apt-get update && apt-get install -y netcat-traditional && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем остальное содержимое проекта
COPY . .

# Копируем скрипт точки входа и делаем его исполняемым
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Указываем, какой порт слушает приложение
EXPOSE 8000

# Указываем, что нужно запустить наш скрипт при старте контейнера
ENTRYPOINT ["/app/entrypoint.sh"]

# CMD остается пустым, так как используется ENTRYPOINT
CMD []