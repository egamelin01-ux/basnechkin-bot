# Инструкция по применению изменений в коде

## Вариант 1: Для разработки (быстрое применение изменений)

Используйте `docker-compose.dev.yml`, который монтирует код через volume. 
Изменения применяются автоматически после перезапуска контейнера.

```bash
# Остановите текущий контейнер
docker-compose down

# Запустите с dev конфигурацией
docker-compose -f docker-compose.dev.yml up -d --build

# После изменения кода просто перезапустите контейнер
docker-compose -f docker-compose.dev.yml restart basnechkin-bot

# Или пересоздайте контейнер (если добавили новые зависимости)
docker-compose -f docker-compose.dev.yml up -d --force-recreate
```

**Преимущества:**
- ✅ Изменения применяются быстро (перезапуск ~5 секунд)
- ✅ Не нужно пересобирать образ каждый раз
- ✅ Удобно для разработки

**Недостатки:**
- ⚠️ Медленнее запуск (при первом запуске)
- ⚠️ Требует перезапуска контейнера после изменений

## Вариант 2: Для продакшена (текущий подход)

Используйте обычный `docker-compose.yml`. 
Код встроен в образ, требуется полная пересборка.

```bash
# После изменения кода
docker-compose down

# Пересоберите образ с новым кодом
docker-compose build --no-cache

# Запустите контейнер
docker-compose up -d

# Или одной командой
docker-compose up -d --build
```

**Преимущества:**
- ✅ Более надежно для production
- ✅ Код изолирован в образе
- ✅ Можно тестировать образ перед деплоем

**Недостатки:**
- ⚠️ Пересборка занимает время (~1-2 минуты)
- ⚠️ Нужно ждать сборки после каждого изменения

## Рекомендация

- **Для разработки:** используйте `docker-compose.dev.yml`
- **Для продакшена:** используйте обычный `docker-compose.yml`

## Быстрая команда для разработки

Создайте файл `restart.sh` (Linux/Mac) или `restart.bat` (Windows):

### Windows (restart.bat):
```batch
@echo off
docker-compose -f docker-compose.dev.yml restart basnechkin-bot
echo Контейнер перезапущен
```

### Linux/Mac (restart.sh):
```bash
#!/bin/bash
docker-compose -f docker-compose.dev.yml restart basnechkin-bot
echo "Контейнер перезапущен"
```

Затем просто запускайте `restart.bat` (или `restart.sh`) после каждого изменения кода.

