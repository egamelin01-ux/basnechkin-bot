# Используем официальный образ Python
FROM python:3.11-slim

# Устанавливаем рабочую директорию
WORKDIR /app

# Копируем файл зависимостей
COPY requirements.txt .

# Устанавливаем зависимости
RUN pip install --no-cache-dir -r requirements.txt

# Копируем весь проект
COPY . .

# Создаем директорию для логов (если нужно)
RUN mkdir -p /app/logs

# Переменные окружения будут переданы через docker-compose или docker run
# DATABASE_URL должен указывать на внешний сервер AlwaysData

# Запускаем бота
CMD ["python", "main.py"]

