# Инструкция по публикации образа в Docker Hub

## Подготовка

### 1. Регистрация в Docker Hub

1. Перейдите на [Docker Hub](https://hub.docker.com/)
2. Зарегистрируйте аккаунт или войдите в существующий
3. Запомните ваше имя пользователя (username)

### 2. Авторизация в Docker

Выполните команду для входа в Docker Hub:

```bash
docker login
```

Введите ваши учетные данные Docker Hub.

## Сборка и публикация образа

### Способ 1: Использование скрипта (рекомендуется)

Используйте готовый скрипт `push_to_dockerhub.bat`:

```bash
push_to_dockerhub.bat [ваш_username] [тег]
```

**Примеры:**

```bash
# С тегом latest (по умолчанию)
push_to_dockerhub.bat myusername

# С конкретным тегом
push_to_dockerhub.bat myusername v1.0.0

# С тегом latest (явно)
push_to_dockerhub.bat myusername latest
```

### Способ 2: Ручная сборка и пуш

```bash
# 1. Сборка образа
docker build -t ваш_username/basnechkin-bot:latest .

# 2. Пуш образа
docker push ваш_username/basnechkin-bot:latest
```

## Использование образа из Docker Hub

### Вариант 1: Docker run

```bash
docker run -d \
  --name basnechkin-bot \
  --env-file .env \
  -v ./logs:/app/logs \
  ваш_username/basnechkin-bot:latest
```

### Вариант 2: Docker Compose

Обновите файл `docker-compose.yml`:

```yaml
services:
  basnechkin-bot:
    image: ваш_username/basnechkin-bot:latest
    container_name: basnechkin-bot
    restart: unless-stopped
    env_file:
      - .env
    volumes:
      - ./logs:/app/logs
```

Затем запустите:

```bash
docker-compose up -d
```

## Важные замечания

### Безопасность

⚠️ **ВАЖНО**: Файлы с секретами (`.env`, `credentials.json`, `service_account.json`) **НЕ** включаются в образ благодаря `.dockerignore`.

При запуске контейнера необходимо:
1. Передать переменные окружения через `env_file` или `environment`
2. Смонтировать файлы с ключами как volumes (если требуется)

### Структура тегов

Рекомендуется использовать семантическое версионирование:

- `latest` - последняя версия (по умолчанию)
- `v1.0.0` - конкретная версия
- `v1.0.0-beta` - бета-версия

### Обновление образа

При обновлении кода:

1. Соберите и запушьте новый образ с новым тегом:
   ```bash
   push_to_dockerhub.bat myusername v1.0.1
   ```

2. Обновите тег `latest`:
   ```bash
   docker tag myusername/basnechkin-bot:v1.0.1 myusername/basnechkin-bot:latest
   docker push myusername/basnechkin-bot:latest
   ```

3. На сервере обновите образ:
   ```bash
   docker pull myusername/basnechkin-bot:latest
   docker-compose up -d
   ```

## Проверка публикации

После пуша проверьте, что образ доступен:

1. Перейдите на https://hub.docker.com/r/ваш_username/basnechkin-bot
2. Убедитесь, что образ виден в списке

## Устранение проблем

### Ошибка "denied: requested access to the resource is denied"

- Убедитесь, что вы авторизованы: `docker login`
- Проверьте правильность имени пользователя

### Ошибка "unauthorized: authentication required"

- Выполните `docker login` заново
- Проверьте, что токен доступа не истек

### Образ слишком большой

- Проверьте `.dockerignore` - убедитесь, что ненужные файлы исключены
- Используйте multi-stage build (если требуется оптимизация)

