# Быстрая инструкция: Пуш в Docker Hub

## Шаг 1: Авторизация

```bash
docker login
```

Введите ваши учетные данные Docker Hub.

## Шаг 2: Пуш образа

```bash
push_to_dockerhub.bat ваш_username
```

Где `ваш_username` - ваше имя пользователя на Docker Hub.

## Шаг 3: Проверка

Перейдите на https://hub.docker.com/r/ваш_username/basnechkin-bot и убедитесь, что образ опубликован.

## Использование

После публикации используйте образ в `docker-compose.yml`:

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

---

**Подробная документация:** см. [DOCKERHUB_SETUP.md](DOCKERHUB_SETUP.md)

