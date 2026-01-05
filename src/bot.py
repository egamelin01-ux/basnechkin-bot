"""Основной файл Telegram-бота 'Баснечкин'."""
import logging
import random
from typing import Dict

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    CallbackQueryHandler,
    filters,
    ContextTypes
)

from config import TELEGRAM_BOT_TOKEN
from db.repository import (
    get_user,
    upsert_user_profile,
    update_user_fields,
    save_story,
    delete_user_profile,
)
from agent_router import AgentRouter
from deepseek_client import DeepSeekClient
from utils import AntifloodManager, ProfileCache, split_message

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# Состояния FSM для анкеты
ASKING_NAME, ASKING_AGE, ASKING_TRAITS, ASKING_SITUATION = range(4)

# Состояния FSM для изменения басни
ASKING_NEW_DILEMMA, ASKING_TRAITS_ADDITION = range(4, 6)

# Инициализация компонентов
agent_router = AgentRouter()
deepseek_client = DeepSeekClient()
antiflood = AntifloodManager()
profile_cache = ProfileCache()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик команды /start."""
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or ""
    
    logger.info(f"Пользователь {user_id} ({username}) запустил бота")
    
    # Проверяем, есть ли уже профиль
    profile = get_user(user_id)
    if profile:
        # Профиль уже есть, просто приветствуем
        await update.message.reply_text(
            "👋 С возвращением! Я готов написать для вас новую басню.\n\n"
            "Просто напишите, о чем должна быть басня, или опишите ситуацию, которую нужно проработать."
        )
        return ConversationHandler.END
    
    # Отправляем приветственные сообщения
    await update.message.reply_text(
        "👋 Здравствуйте! Я Баснечкин.\n\n"
        "Моя задача — помогать родителям наставлять ребёнка через художественные басни "
        "по мотивам басен Крылова И.А., в которых ребёнок становится персонажем истории."
    )
    
    await update.message.reply_text(
        "Сейчас я задам вам несколько вопросов про вашего ребенка, "
        "чтобы в наших баснях главными героями были именно ваши дети."
    )
    
    # Начинаем анкету
    await update.message.reply_text("Как зовут вашего ребенка (детей)?")
    
    return ASKING_NAME


async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ответа на вопрос об имени."""
    child_names = update.message.text.strip()
    context.user_data['child_names'] = child_names
    
    await update.message.reply_text("Сколько лет?:)")
    return ASKING_AGE


async def handle_age(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ответа на вопрос о возрасте."""
    age = update.message.text.strip()
    context.user_data['age'] = age
    
    await update.message.reply_text(
        "Опишите, пожалуйста, какими основными чертами характера отличается ваш ребенок?\n\n"
        "Например: спокойный, любознательный, стеснительный, упрямый, добрый и т.д."
    )
    return ASKING_TRAITS


async def handle_traits(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ответа на вопрос о чертах характера."""
    traits = update.message.text.strip()
    user_id = update.effective_user.id
    username = update.effective_user.username or update.effective_user.first_name or ""
    
    # Сохраняем профиль
    child_names = context.user_data.get('child_names', '')
    age = context.user_data.get('age', '')
    
    success = upsert_user_profile(
        telegram_id=user_id,
        username=username,
        child_names=child_names,
        age=age,
        traits=traits
    )
    
    if not success:
        await update.message.reply_text(
            "Произошла ошибка при сохранении профиля. Попробуйте позже."
        )
        return ConversationHandler.END
    
    # Инвалидируем кэш
    profile_cache.invalidate(user_id)
    
    # Задаем 4-й вопрос о ситуации
    await update.message.reply_text(
        "Хотите разобрать какую-то реальную ситуацию, связанную с ребёнком?\n\n"
        "Мы можем добавить в сказку дилемму (например: не любит делиться, дерётся во дворе, не слушается) "
        "и сделать поучительную басню с моралью именно под эту ситуацию.\n\n"
        "Если хотите — опишите её своими словами. Если нет — просто напишите \"нет\"."
    )
    
    return ASKING_SITUATION


async def handle_situation(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ответа на вопрос о ситуации."""
    user_id = update.effective_user.id
    answer = update.message.text.strip()
    
    # Проверяем, ответил ли пользователь "нет"
    if answer.lower() == "нет":
        # Context не меняется (остается NULL или предыдущий)
        await update.message.reply_text(
            "Понятно. Сейчас я напишу для вас первую басню."
        )
        # Генерируем обычную басню
        await generate_and_send_story(update, context, "Напиши первую басню-знакомство с ребенком.")
        return ConversationHandler.END
    else:
        # Сохраняем ситуацию в context_active
        success = update_user_fields(user_id, context_active=answer)
        if success:
            # Инвалидируем кэш
            profile_cache.invalidate(user_id)
            updated_profile = get_user(user_id)
            if updated_profile:
                profile_cache.set(user_id, updated_profile)
            
            await update.message.reply_text(
                "Отлично! Учту эту ситуацию в басне. Сейчас напишу для вас первую басню с разбором этой ситуации."
            )
            # Генерируем басню с учетом ситуации
            await generate_and_send_story(
                update, 
                context, 
                f"Напиши первую басню-знакомство с ребенком, которая разбирает ситуацию: {answer}"
            )
        else:
            await update.message.reply_text(
                "Произошла ошибка при сохранении. Попробуйте позже."
            )
        
        return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена анкеты."""
    await update.message.reply_text("Анкета отменена. Используйте /start для начала.")
    return ConversationHandler.END


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /reset - сброс профиля и начало заново."""
    user_id = update.effective_user.id
    
    # Проверяем, есть ли профиль
    profile = get_user(user_id)
    if not profile:
        await update.message.reply_text(
            "У вас нет сохраненного профиля. Используйте /start для регистрации."
        )
        return
    
    # Удаляем профиль и все басни
    success = delete_user_profile(user_id)
    
    if success:
        # Инвалидируем кэш
        profile_cache.invalidate(user_id)
        
        # Очищаем данные из context
        context.user_data.clear()
        
        await update.message.reply_text(
            "✅ Профиль и все басни удалены.\n\n"
            "Теперь вы можете начать заново. Используйте /start для регистрации."
        )
        logger.info(f"Пользователь {user_id} сбросил профиль")
    else:
        await update.message.reply_text(
            "❌ Произошла ошибка при удалении профиля. Попробуйте позже."
        )


async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик обычных сообщений пользователя."""
    user_id = update.effective_user.id
    user_message = update.message.text.strip()
    
    # Проверяем, не находимся ли мы в состоянии ConversationHandler
    if context.user_data.get('waiting_for'):
        logger.warning(f"Сообщение от пользователя {user_id} перехвачено handle_message, но ожидается: {context.user_data.get('waiting_for')}")
    
    logger.info(f"Пользователь {user_id} отправил сообщение: {user_message[:50]}...")
    
    # Проверяем наличие профиля
    profile = profile_cache.get(user_id)
    if not profile:
        profile = get_user(user_id)
        if profile:
            profile_cache.set(user_id, profile)
        else:
            # Профиля нет, просим начать с /start
            await update.message.reply_text(
                "Для начала работы с ботом используйте команду /start"
            )
            return
    
    # Проверяем антифлуд
    can_gen, message = antiflood.can_generate(user_id)
    if not can_gen:
        await update.message.reply_text(message)
        return
    
    # Начинаем генерацию
    antiflood.start_generation(user_id)
    
    try:
        await generate_and_send_story(update, context, user_message)
    finally:
        antiflood.finish_generation(user_id)


def create_story_options_keyboard() -> InlineKeyboardMarkup:
    """Создает клавиатуру с кнопками выбора для следующей басни."""
    keyboard = [
        [InlineKeyboardButton("1️⃣ Новая дилемма", callback_data="story_new_dilemma")],
        [InlineKeyboardButton("2️⃣ Со случайной моралью", callback_data="story_random_moral")],
        [InlineKeyboardButton("3️⃣ Прошлая мораль", callback_data="story_previous_moral")],
        [InlineKeyboardButton("4️⃣ Дополнить характер", callback_data="story_add_traits")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def show_story_options(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Показывает кнопки выбора для следующей басни."""
    text = (
        "📖 Будем ли что-то менять в следующей басне?\n\n"
        "Выберите один из вариантов:"
    )
    
    # Определяем, откуда отправлять сообщение
    if update.message:
        await update.message.reply_text(text, reply_markup=create_story_options_keyboard())
    elif update.callback_query:
        # Для callback_query отправляем новое сообщение
        await update.callback_query.message.reply_text(text, reply_markup=create_story_options_keyboard())


async def handle_story_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик callback для кнопок выбора басни."""
    query = update.callback_query
    await query.answer()
    
    user_id = update.effective_user.id
    callback_data = query.data
    logger.info(f"Обработка callback {callback_data} для пользователя {user_id}")
    
    # Проверяем наличие профиля
    profile = profile_cache.get(user_id)
    if not profile:
        profile = get_user(user_id)
        if profile:
            profile_cache.set(user_id, profile)
        else:
            await query.message.reply_text(
                "Произошла ошибка при загрузке профиля. Используйте /start для повторной регистрации."
            )
            return
    
    # Дополнительная проверка: убеждаемся, что profile - это словарь
    if not isinstance(profile, dict):
        logger.error(f"Профиль имеет неверный тип для пользователя {user_id}: {type(profile)}")
        await query.message.reply_text(
            "Произошла ошибка при загрузке профиля. Используйте /start для повторной регистрации."
        )
        return
    
    # Обрабатываем разные типы callback
    if callback_data == "story_new_dilemma":
        # Новая дилемма - просим описать ситуацию
        await query.message.reply_text(
            "Опишите новую ситуацию или дилемму, которую хотите разобрать в следующей басне:\n\n"
            "Например: не любит делиться, дерётся во дворе, не слушается и т.д."
        )
        context.user_data['waiting_for'] = 'new_dilemma'
        return ASKING_NEW_DILEMMA
    
    elif callback_data == "story_random_moral":
        # Со случайной моралью - сразу генерируем
        await query.message.reply_text("✒️ Пишу басню со случайной моралью...")
        await generate_story_with_random_moral(update, context, user_id, profile)
        return ConversationHandler.END
    
    elif callback_data == "story_previous_moral":
        # Прошлая мораль - используем context_active
        context_active = profile.get('context_active', '').strip() if profile.get('context_active') else ''
        if not context_active:
            await query.message.reply_text(
                "У вас нет сохраненной ситуации. Выберите другой вариант или опишите новую дилемму."
            )
            await show_story_options(update, context)
            return ConversationHandler.END
        
        await query.message.reply_text("✒️ Пишу басню с прошлой моралью...")
        await generate_story_with_previous_moral(update, context, user_id, profile, context_active)
        return ConversationHandler.END
    
    elif callback_data == "story_add_traits":
        # Дополнить характер - просим описать дополнения
        logger.info(f"Пользователь {user_id} выбрал 'Дополнить характер'")
        await query.message.reply_text(
            "Опишите, какие черты характера вы хотите добавить к существующему описанию:\n\n"
            "Например: также очень любознательный, иногда бывает упрямым и т.д."
        )
        context.user_data['waiting_for'] = 'add_traits'
        logger.info(f"Переход в состояние ASKING_TRAITS_ADDITION для пользователя {user_id}")
        return ASKING_TRAITS_ADDITION
    
    logger.warning(f"Неизвестный callback_data: {callback_data} для пользователя {user_id}")
    return ConversationHandler.END


async def handle_new_dilemma(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ответа на вопрос о новой дилемме."""
    user_id = update.effective_user.id
    dilemma = update.message.text.strip()
    
    # Обновляем context_active в БД
    success = update_user_fields(user_id, context_active=dilemma)
    if not success:
        await update.message.reply_text(
            "Произошла ошибка при сохранении. Попробуйте позже."
        )
        return ConversationHandler.END
    
    # Инвалидируем кэш
    profile_cache.invalidate(user_id)
    updated_profile = get_user(user_id)
    if updated_profile:
        profile_cache.set(user_id, updated_profile)
    
    # Генерируем басню с новой дилеммой
    await update.message.reply_text("✒️ Пишу басню с новой дилеммой...")
    await generate_story_with_new_dilemma(update, context, user_id, updated_profile, dilemma)
    
    return ConversationHandler.END


async def handle_traits_addition(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ответа на вопрос о дополнении характера."""
    user_id = update.effective_user.id
    logger.info(f"Получен ответ на дополнение характера от пользователя {user_id}")
    new_traits = update.message.text.strip()
    
    # Получаем текущий профиль
    profile = profile_cache.get(user_id)
    if not profile:
        profile = get_user(user_id)
        if profile:
            profile_cache.set(user_id, profile)
    
    if not profile:
        await update.message.reply_text(
            "Произошла ошибка при загрузке профиля. Попробуйте позже."
        )
        return ConversationHandler.END
    
    # Добавляем новые черты к существующим
    current_traits = profile.get('traits', '').strip()
    if current_traits:
        updated_traits = f"{current_traits}. {new_traits}"
    else:
        updated_traits = new_traits
    
    # Обновляем traits в БД
    success = update_user_fields(user_id, traits=updated_traits)
    if not success:
        await update.message.reply_text(
            "Произошла ошибка при сохранении. Попробуйте позже."
        )
        return ConversationHandler.END
    
    # Инвалидируем кэш
    profile_cache.invalidate(user_id)
    updated_profile = get_user(user_id)
    if updated_profile:
        profile_cache.set(user_id, updated_profile)
    
    # Генерируем басню с обновленным характером
    await update.message.reply_text("✒️ Пишу басню с учетом дополнений к характеру...")
    await generate_story_with_updated_traits(update, context, user_id, updated_profile)
    
    return ConversationHandler.END


async def generate_story_with_new_dilemma(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    profile: Dict,
    dilemma: str
):
    """Генерирует басню с новой дилеммой."""
    try:
        # Используем агент-роутер для формирования промпта
        agent_response = agent_router.process_story_request(
            request_type="new_dilemma",
            user_message=dilemma,
            user_profile=profile
        )
        
        await generate_and_send_story_internal(update, context, user_id, profile, agent_response)
    except Exception as e:
        logger.error(f"Ошибка при генерации басни с новой дилеммой: {e}", exc_info=True)
        message_target = update.message if update.message else (update.callback_query.message if update.callback_query else None)
        if message_target:
            await message_target.reply_text(
                "❌ Произошла ошибка при генерации басни. Попробуйте позже."
            )


async def generate_story_with_random_moral(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    profile: Dict
):
    """Генерирует басню со случайной моралью."""
    message_target = update.message if update.message else (update.callback_query.message if update.callback_query else None)
    
    try:
        # Проверяем, что profile не None и не пустой
        if not profile:
            logger.error(f"Профиль пустой или None для пользователя {user_id}")
            if message_target:
                await message_target.reply_text(
                    "❌ Ошибка: профиль не найден. Используйте /start для регистрации."
                )
            return
        
        # Используем агент-роутер для формирования промпта
        agent_response = agent_router.process_story_request(
            request_type="random_moral",
            user_message="",
            user_profile=profile
        )
        
        # Проверяем, что agent_response содержит нужные данные
        if not agent_response or "deepseek_user_prompt" not in agent_response:
            logger.error(f"Некорректный ответ от agent_router для пользователя {user_id}: {agent_response}")
            if message_target:
                await message_target.reply_text(
                    "❌ Ошибка при формировании запроса. Попробуйте позже."
                )
            return
        
        await generate_and_send_story_internal(update, context, user_id, profile, agent_response)
    except Exception as e:
        logger.error(f"Ошибка при генерации басни со случайной моралью: {e}", exc_info=True)
        if message_target:
            await message_target.reply_text(
                "❌ Произошла ошибка при генерации басни. Попробуйте позже."
            )


async def generate_story_with_previous_moral(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    profile: Dict,
    context_active: str
):
    """Генерирует басню с прошлой моралью."""
    try:
        # Используем агент-роутер для формирования промпта
        agent_response = agent_router.process_story_request(
            request_type="previous_moral",
            user_message=context_active,
            user_profile=profile
        )
        
        await generate_and_send_story_internal(update, context, user_id, profile, agent_response)
    except Exception as e:
        logger.error(f"Ошибка при генерации басни с прошлой моралью: {e}", exc_info=True)
        message_target = update.message if update.message else (update.callback_query.message if update.callback_query else None)
        if message_target:
            await message_target.reply_text(
                "❌ Произошла ошибка при генерации басни. Попробуйте позже."
            )


async def generate_story_with_updated_traits(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    profile: Dict
):
    """Генерирует басню с обновленным характером."""
    try:
        # Используем агент-роутер для формирования промпта
        agent_response = agent_router.process_story_request(
            request_type="add_traits",
            user_message="",
            user_profile=profile
        )
        
        await generate_and_send_story_internal(update, context, user_id, profile, agent_response)
    except Exception as e:
        logger.error(f"Ошибка при генерации басни с обновленным характером: {e}", exc_info=True)
        message_target = update.message if update.message else (update.callback_query.message if update.callback_query else None)
        if message_target:
            await message_target.reply_text(
                "❌ Произошла ошибка при генерации басни. Попробуйте позже."
            )


async def generate_and_send_story_internal(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    profile: Dict,
    agent_response: Dict
):
    """Внутренняя функция для генерации и отправки басни."""
    message_target = update.message if update.message else (update.callback_query.message if update.callback_query else None)
    
    try:
        # Определяем, откуда отправлять сообщения
        if not message_target:
            logger.error(f"Не удалось определить target для отправки сообщения для пользователя {user_id}")
            return
        
        # Проверяем, что agent_response не пустой
        if not agent_response:
            logger.error(f"Пустой agent_response для пользователя {user_id}")
            await message_target.reply_text(
                "❌ Ошибка при формировании запроса. Попробуйте позже."
            )
            return
        
        # Генерируем басню через DeepSeek
        deepseek_prompt = agent_response.get("deepseek_user_prompt", "")
        if not deepseek_prompt:
            logger.error(f"Пустой промпт от Agent 1 для пользователя {user_id}, agent_response: {agent_response}")
            await message_target.reply_text(
                "❌ Ошибка при формировании запроса. Попробуйте позже."
            )
            return
        
        # ВАЖНО: Добавляем информацию о детях из профиля в начало промпта
        if profile and isinstance(profile, dict):
            child_names = profile.get('child_names', '').strip() if profile.get('child_names') else ''
            age = profile.get('age', '').strip() if profile.get('age') else ''
            traits = profile.get('traits', '').strip() if profile.get('traits') else ''
            context_active = profile.get('context_active', '').strip() if profile.get('context_active') else ''
            request_type = agent_response.get("request_type", "regular")
            
            profile_header = f"ГЛАВНЫЕ ГЕРОИ БАСНИ (обязательно используй их в басне):\n"
            profile_header += f"- Имена: {child_names}\n"
            if age:
                profile_header += f"- Возраст: {age}\n"
            if traits:
                profile_header += f"- Черты характера: {traits}\n"
            
            # Для случайной морали НЕ добавляем context_active
            if request_type != "random_moral" and context_active:
                profile_header += f"\nВАЖНО - РЕАЛЬНАЯ СИТУАЦИЯ ДЛЯ РАЗБОРА:\n{context_active}\n"
                profile_header += "Басня ОБЯЗАТЕЛЬНО должна разбирать именно эту ситуацию с явной моралью в конце.\n"
            
            profile_header += f"\nЗАДАНИЕ: {deepseek_prompt}\n\n"
            profile_header += "ВАЖНО: Главными героями басни ДОЛЖНЫ быть именно эти дети с указанными именами и чертами характера."
            deepseek_prompt = profile_header
            
            logger.info(f"Добавлена информация о детях в промпт: {child_names}")
            if request_type != "random_moral" and context_active:
                logger.info(f"Добавлен контекст ситуации: {context_active[:100]}...")
        else:
            logger.warning(f"Профиль не найден или некорректен для пользователя {user_id}, используем базовый промпт")
        
        logger.info(f"Генерирую басню через DeepSeek для пользователя {user_id}, длина промпта: {len(deepseek_prompt)}")
        story_text = deepseek_client.generate_story(deepseek_prompt)
        
        if not story_text:
            logger.error(f"DeepSeek вернул пустой ответ для пользователя {user_id}")
            await message_target.reply_text(
                "❌ Произошла ошибка при генерации басни. Попробуйте позже."
            )
            return
        
        # Сохраняем басню в БД
        try:
            save_story(user_id, story_text, model='deepseek')
        except Exception as e:
            logger.error(f"Ошибка при сохранении басни в БД для пользователя {user_id}: {e}", exc_info=True)
            # Продолжаем отправку, даже если сохранение не удалось
        
        # Отправляем басню частями, если она длинная
        chunks = split_message(story_text)
        for i, chunk in enumerate(chunks):
            if i == 0:
                await message_target.reply_text(chunk)
            else:
                await message_target.reply_text(chunk)
        
        # Показываем кнопки выбора для следующей басни
        await show_story_options(update, context)
        
        logger.info(f"Басня успешно отправлена пользователю {user_id}")
        
    except Exception as e:
        logger.error(f"Ошибка при генерации басни для пользователя {user_id}: {e}", exc_info=True)
        if message_target:
            try:
                await message_target.reply_text(
                    "❌ Произошла ошибка при генерации басни. Попробуйте позже."
                )
            except Exception as send_error:
                logger.error(f"Ошибка при отправке сообщения об ошибке пользователю {user_id}: {send_error}", exc_info=True)


async def generate_and_send_story(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_message: str
):
    """Пишет басню и отправляет пользователю."""
    user_id = update.effective_user.id
    
    try:
        # Загружаем профиль (из кэша или из БД)
        profile = profile_cache.get(user_id)
        if not profile:
            profile = get_user(user_id)
            if profile:
                profile_cache.set(user_id, profile)
        
        if not profile:
            await update.message.reply_text(
                "Произошла ошибка при загрузке профиля. Используйте /start для повторной регистрации."
            )
            return
        
        # Отправляем индикатор генерации
        status_msg = await update.message.reply_text("✒️ Пишу басню...")
        
        # Вызываем Agent 1
        try:
            agent_response = agent_router.process_message(user_message, profile)
            logger.info(f"Agent 1 ответ получен для пользователя {user_id}")
        except Exception as e:
            logger.error(f"Ошибка при вызове Agent 1: {e}", exc_info=True)
            await status_msg.edit_text(
                "❌ Ошибка при обработке запроса. Попробуйте позже."
            )
            return
        
        # Обновляем профиль, если нужно
        if agent_response.get("should_update_profile", False):
            profile_patch = agent_response.get("profile_patch", {})
            if profile_patch:
                # Обновляем только существующие поля (last_user_message не используется в новой схеме БД)
                success = update_user_fields(user_id, **profile_patch)
                if success:
                    # Инвалидируем кэш и обновляем
                    profile_cache.invalidate(user_id)
                    updated_profile = get_user(user_id)
                    if updated_profile:
                        profile_cache.set(user_id, updated_profile)
                        profile = updated_profile
        
        # Удаляем статус-сообщение перед генерацией
        await status_msg.delete()
        
        # Используем внутреннюю функцию для генерации
        agent_response['request_type'] = 'regular'  # Обычный запрос
        await generate_and_send_story_internal(update, context, user_id, profile, agent_response)
        
    except Exception as e:
        logger.error(f"Ошибка при генерации басни для пользователя {user_id}: {e}", exc_info=True)
        try:
            await status_msg.edit_text(
                "❌ Произошла ошибка при генерации басни. Попробуйте позже."
            )
        except:
            await update.message.reply_text(
                "❌ Произошла ошибка при генерации басни. Попробуйте позже."
            )


def main():
    """Запуск бота."""
    logger.info("Запуск бота 'Баснечкин'...")
    
    # Создаем приложение
    application = Application.builder().token(TELEGRAM_BOT_TOKEN).build()
    
    # ConversationHandler для анкеты
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler("start", start_command)],
        states={
            ASKING_NAME: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_name)],
            ASKING_AGE: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_age)],
            ASKING_TRAITS: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_traits)],
            ASKING_SITUATION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_situation)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # ConversationHandler для изменения басни
    story_modify_handler = ConversationHandler(
        entry_points=[CallbackQueryHandler(handle_story_callback, pattern="^story_")],
        states={
            ASKING_NEW_DILEMMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_dilemma)],
            ASKING_TRAITS_ADDITION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_traits_addition)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(conv_handler)
    application.add_handler(story_modify_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запускаем бота
    logger.info("Бот запущен и готов к работе")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

