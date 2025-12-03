# Используем официальный образ Python как базовый
FROM python:3.11-slim

# Устанавливаем рабочую директорию внутри контейнера
WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
# Установка netcat (nc) для проверки доступности порта 5432
RUN apt-get update && apt-get install -y netcat-traditional && rm -rf /var/lib/apt/lists/*
RUN pip install --no-cache-dir -r requirements.txt

# Копируем все остальное содержимое проекта в контейнер
COPY . .

# КОПИРУЕМ СКРИПТ, ДЕЛАЕМ ИСПОЛНЯЕМЫМ И ЗАПУСКАЕМ!
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Указываем, какой порт использует приложение (для API-сервиса)
EXPOSE 8000

# Указываем, что нужно запустить наш скрипт
ENTRYPOINT ["/app/entrypoint.sh"]

# CMD остается пустым, так как он не используется с ENTRYPOINT,
# но мы оставим его здесь для ясности (хотя он будет проигнорирован)
CMD []