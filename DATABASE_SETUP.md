# Настройка подключения к PostgreSQL (AlwaysData)

## Шаг 1: Получение данных для подключения от AlwaysData

1. Войдите в панель управления AlwaysData: https://admin.alwaysdata.com/
2. Перейдите в раздел **Базы данных** → **PostgreSQL**
3. Если база данных еще не создана:
   - Нажмите **Создать базу данных**
   - Выберите версию PostgreSQL (рекомендуется 14+)
   - Запишите имя базы данных, пользователя и пароль

4. Найдите информацию о подключении:
   - **Хост (host)**: обычно `postgresql-[ваш-аккаунт].alwaysdata.net` или `localhost` (если подключаетесь с сервера)
   - **Порт (port)**: обычно `5432`
   - **Имя базы данных (database)**: имя, которое вы создали
   - **Пользователь (user)**: имя пользователя БД
   - **Пароль (password)**: пароль, который вы задали

## Шаг 2: Формирование DATABASE_URL

Формат DATABASE_URL для PostgreSQL:
```
postgresql://username:password@host:port/database
```

Пример:
```
postgresql://myuser:mypassword@postgresql-myaccount.alwaysdata.net:5432/mybotdb
```

**Важно:**
- Если в пароле есть специальные символы (например, `@`, `#`, `:`), их нужно закодировать в URL-формат:
  - `@` → `%40`
  - `#` → `%23`
  - `:` → `%3A`
  - и т.д.

## Шаг 3: Добавление DATABASE_URL в .env

Откройте файл `.env` в корне проекта и добавьте строку:

```env
DATABASE_URL=postgresql://username:password@host:port/database
```

**Пример:**
```env
# Telegram Bot Token
TELEGRAM_BOT_TOKEN=your_token_here

# OpenAI API Key
OPENAI_API_KEY=your_key_here

# DeepSeek API
DEEPSEEK_API_KEY=your_key_here
DEEPSEEK_API_URL=https://api.deepseek.com/v1/chat/completions

# PostgreSQL Database (AlwaysData)
DATABASE_URL=postgresql://myuser:mypassword@postgresql-myaccount.alwaysdata.net:5432/mybotdb

# Настройки
ANTIFLOOD_SECONDS=15
PROFILE_CACHE_TTL_MINUTES=5
```

## Шаг 4: Проверка подключения

После добавления DATABASE_URL выполните:

```bash
# Проверьте подключение к базе данных
python test_db.py
```

Если подключение успешно, вы увидите:
```
✓ DATABASE_URL найден: postgresql://myuser:***@host:port/database
✓ Подключение к базе данных успешно
✓ Все таблицы присутствуют: ['users', 'stories', 'contexts']
✓ Пользователь создан
✓ Пользователь получен
✓ Басня сохранена
✓ Тестовый пользователь удален

✅ Все тесты пройдены успешно!
```

Если таблицы отсутствуют, выполните миграции:

```bash
alembic upgrade head
```

## Шаг 5: Применение миграций

Если база данных новая (пустая), нужно создать таблицы:

```bash
alembic upgrade head
```

Вы должны увидеть:
```
INFO  [alembic.runtime.migration] Context impl PostgresqlImpl.
INFO  [alembic.runtime.migration] Will assume transactional DDL.
INFO  [alembic.runtime.migration] Running upgrade  -> 001_initial, Initial migration
```

## Возможные проблемы

### Ошибка подключения
- Проверьте правильность DATABASE_URL
- Убедитесь, что база данных создана в AlwaysData
- Проверьте, что хост и порт указаны правильно
- Убедитесь, что пароль закодирован, если содержит специальные символы

### Ошибка "Таблицы отсутствуют"
- Выполните: `alembic upgrade head`

### Ошибка прав доступа
- Убедитесь, что пользователь БД имеет права на создание таблиц
- В AlwaysData пользователь обычно имеет все необходимые права

## Дополнительная информация

После настройки подключения бот будет использовать PostgreSQL вместо Google Sheets для хранения:
- Профилей пользователей (таблица `users`)
- Историй/басен (таблица `stories`, максимум 5 на пользователя)
- Контекстов (таблица `contexts`, если используется)

Все данные будут автоматически сохраняться в PostgreSQL при работе бота.

