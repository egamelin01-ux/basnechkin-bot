# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Устанавливаем системные зависимости (если нужны)
# RUN apt-get update && apt-get install -y --no-install-recommends \
#     && rm -rf /var/lib/apt/lists/*

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости Python
RUN pip install --no-cache-dir --upgrade pip && \
    pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаем директорию для логов
RUN mkdir -p /app/logs && \
    chmod 755 /app/logs

# Переменные окружения будут переданы через docker-compose или docker run
# DATABASE_URL должен указывать на внешний сервер AlwaysData

# Запускаем бота
CMD ["python", "main.py"]

