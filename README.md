# Басенник - Telegram-бот для генерации басен

Telegram-бот, который помогает родителям наставлять детей через художественные басни по мотивам басен Крылова И.А., в которых ребёнок становится персонажем истории.

## Технологии

- **Python 3.11+**
- **python-telegram-bot 21+** - работа с Telegram API
- **OpenAI API** - Agent 1 (роутер логики и генератор промптов)
- **DeepSeek API** - генерация текста басен
- **Google Sheets API** - база данных профилей и последних 5 басен на пользователя

## Структура проекта

```
basnechkin-bot/
├── src/
│   ├── __init__.py
│   ├── bot.py              # Основной файл бота
│   ├── config.py           # Конфигурация и переменные окружения
│   ├── sheets.py           # Работа с Google Sheets
│   ├── agent_router.py     # Agent 1 (OpenAI)
│   ├── deepseek_client.py  # Клиент DeepSeek API
│   └── utils.py            # Утилиты (антифлуд, кэш, разбиение сообщений)
├── main.py                 # Точка входа для запуска бота
├── .env                    # Переменные окружения (создать на основе .env.example)
├── credentials.json        # Ключ сервисного аккаунта Google (скачать)
├── requirements.txt        # Зависимости Python
└── README.md              # Этот файл
```

## Установка и настройка

### 1. Клонирование и установка зависимостей

```bash
# Перейдите в директорию проекта
cd basnechkin-bot

# Создайте виртуальное окружение (рекомендуется)
python -m venv venv

# Активируйте виртуальное окружение
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Установите зависимости
pip install -r requirements.txt
```

### 2. Настройка Google Sheets

#### Шаг 1: Создание сервисного аккаунта

1. Перейдите в [Google Cloud Console](https://console.cloud.google.com/)
2. Создайте новый проект или выберите существующий
3. Перейдите в **APIs & Services** → **Credentials**
4. Нажмите **Create Credentials** → **Service Account**
5. Заполните данные:
   - **Service account name**: `basnechkin-bot`
   - **Service account ID**: автоматически сгенерируется
   - Нажмите **Create and Continue**
6. В разделе **Grant this service account access to project** выберите роль **Editor** (или создайте кастомную роль с доступом к Sheets)
7. Нажмите **Done**

#### Шаг 2: Создание ключа

1. В списке сервисных аккаунтов найдите созданный аккаунт
2. Откройте его и перейдите на вкладку **Keys**
3. Нажмите **Add Key** → **Create new key**
4. Выберите формат **JSON**
5. Нажмите **Create** - файл `credentials.json` скачается автоматически
6. Переместите `credentials.json` в корневую директорию проекта

#### Шаг 3: Создание Google Таблицы

1. Создайте новую Google Таблицу на [Google Sheets](https://sheets.google.com)
2. Назовите её, например, "Басенник БД"
3. Скопируйте **SPREADSHEET_ID** из URL:
   ```
   https://docs.google.com/spreadsheets/d/SPREADSHEET_ID/edit
   ```

#### Шаг 4: Настройка листов в таблице

Создайте два листа в таблице:

**Лист 1: Users** (профили пользователей)

| A | B | C | D | E | F | G | H | I | J |
|---|---|---|---|---|---|---|---|---|---|
| user_id | username | child_names | age | traits | created_at | updated_at | last_user_message | state | version |

**Лист 2: Stories** (басни, максимум 5 на пользователя)

| A | B | C | D | E |
|---|---|---|---|---|
| ts | user_id | story_id | story_text | model |

**Важно:** Первая строка в каждом листе должна содержать заголовки (как показано выше).

#### Шаг 5: Предоставление доступа к таблице

1. В Google Таблице нажмите кнопку **Поделиться** (Share)
2. Вставьте **email сервисного аккаунта** (находится в `credentials.json` в поле `client_email`)
3. Выберите уровень доступа: **Редактор** (Editor)
4. Нажмите **Отправить**

### 3. Получение API ключей

#### Telegram Bot Token

1. Найдите [@BotFather](https://t.me/BotFather) в Telegram
2. Отправьте команду `/newbot`
3. Следуйте инструкциям для создания бота
4. Скопируйте полученный токен

#### OpenAI API Key

1. Перейдите на [OpenAI Platform](https://platform.openai.com/)
2. Зарегистрируйтесь или войдите в аккаунт
3. Перейдите в **API keys**
4. Нажмите **Create new secret key**
5. Скопируйте ключ (он показывается только один раз!)

#### DeepSeek API Key

1. Перейдите на [DeepSeek Platform](https://platform.deepseek.com/)
2. Зарегистрируйтесь или войдите в аккаунт
3. Перейдите в раздел API keys
4. Создайте новый ключ и скопируйте его

### 4. Настройка переменных окружения

1. Скопируйте `.env.example` в `.env`:
   ```bash
   cp .env.example .env
   ```

2. Откройте `.env` и заполните все значения:

```env
# Telegram Bot Token
TELEGRAM_BOT_TOKEN=1234567890:ABCdefGHIjklMNOpqrsTUVwxyz

# OpenAI API Key (для Agent 1)
OPENAI_API_KEY=sk-...

# DeepSeek API
DEEPSEEK_API_KEY=sk-...
DEEPSEEK_API_URL=https://api.deepseek.com/v1/chat/completions

# Google Sheets
GOOGLE_SHEETS_CREDENTIALS_PATH=credentials.json
SPREADSHEET_ID=1a2b3c4d5e6f7g8h9i0j1k2l3m4n5o6p7q8r9s0t

# Настройки
ANTIFLOOD_SECONDS=15
PROFILE_CACHE_TTL_MINUTES=5
```

## Запуск бота

```bash
# Убедитесь, что виртуальное окружение активировано
# Windows:
venv\Scripts\activate
# Linux/Mac:
source venv/bin/activate

# Запустите бота
python main.py
```

Если всё настроено правильно, вы увидите в консоли:
```
INFO - Запуск бота 'Басенник'...
INFO - Google Sheets сервис инициализирован
INFO - Бот запущен и готов к работе
```

## Использование

1. Найдите вашего бота в Telegram по имени, которое вы указали при создании через BotFather
2. Отправьте команду `/start`
3. Ответьте на вопросы анкеты:
   - Имя ребенка (детей)
   - Возраст
   - Черты характера
4. После завершения анкеты бот автоматически сгенерирует первую басню-знакомство
5. В дальнейшем просто отправляйте сообщения боту, и он будет генерировать новые басни

## Особенности

- **Антифлуд**: не более 1 генерации в 15 секунд на пользователя
- **Автоматическое обновление профиля**: бот анализирует сообщения и обновляет информацию о ребенке при необходимости
- **Хранение последних 5 басен**: в Google Sheets хранится только последние 5 басен на пользователя (старые автоматически удаляются)
- **Кэширование профилей**: профили кэшируются на 5 минут для оптимизации
- **Разбиение длинных сообщений**: басни автоматически разбиваются на части, если превышают лимит Telegram

## Устранение неполадок

### Ошибка "TELEGRAM_BOT_TOKEN не установлен"
- Проверьте, что файл `.env` существует и содержит правильный токен
- Убедитесь, что файл называется именно `.env` (не `.env.txt`)

### Ошибка "SPREADSHEET_ID не установлен"
- Проверьте, что в `.env` указан правильный ID таблицы
- ID находится в URL таблицы между `/d/` и `/edit`

### Ошибка доступа к Google Sheets
- Убедитесь, что файл `credentials.json` находится в корне проекта
- Проверьте, что email сервисного аккаунта добавлен в доступ к таблице с правами "Редактор"
- Убедитесь, что листы называются точно "Users" и "Stories" (с заглавными буквами)

### Ошибка генерации басни
- Проверьте правильность API ключей OpenAI и DeepSeek
- Убедитесь, что на счетах есть достаточный баланс
- Проверьте логи в консоли для детальной информации об ошибке

## Docker Hub

Проект готов для публикации в Docker Hub. Подробные инструкции см. в [DOCKERHUB_SETUP.md](DOCKERHUB_SETUP.md).

### Быстрый старт

1. Авторизуйтесь в Docker Hub:
   ```bash
   docker login
   ```

2. Соберите и запушьте образ:
   ```bash
   push_to_dockerhub.bat ваш_username
   ```

3. Используйте образ в docker-compose.yml:
   ```yaml
   services:
     basnechkin-bot:
       image: ваш_username/basnechkin-bot:latest
       # ... остальные настройки
   ```

## Лицензия

Проект создан для личного использования.

