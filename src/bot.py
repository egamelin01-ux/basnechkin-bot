"""Основной файл Telegram-бота 'Баснописец'."""
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

from config import TELEGRAM_BOT_TOKEN, ANTIFLOOD_SECONDS, DAILY_STORY_LIMIT
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

# Состояния FSM для пожеланий
ASKING_WISHES, ASKING_WISHES_EDIT = range(6, 8)

# Инициализация компонентов
agent_router = AgentRouter()
deepseek_client = DeepSeekClient()
antiflood = AntifloodManager(cooldown_seconds=ANTIFLOOD_SECONDS, daily_limit=DAILY_STORY_LIMIT)
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
        ", в которых ребёнок становится персонажем истории."
    )
    
    await update.message.reply_text(
        "Сейчас я задам вам несколько вопросов про вашего ребенка, "
        "чтобы в наших баснях главным героем был именно он."
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
        "Мы можем добавить в басню дилемму (например: не любит делиться, дерётся во дворе, не слушается) "
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
        [InlineKeyboardButton("4️⃣ Дополнить характер", callback_data="story_add_traits")],
        [InlineKeyboardButton("5️⃣ Пожелания", callback_data="story_wishes")]
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
        # Обновляем профиль из БД перед генерацией, чтобы получить актуальные данные
        profile_cache.invalidate(user_id)
        fresh_profile = get_user(user_id)
        if fresh_profile:
            profile_cache.set(user_id, fresh_profile)
            profile = fresh_profile
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
        # Изменить характер - просим описать изменения
        logger.info(f"Пользователь {user_id} выбрал 'Дополнить характер'")
        
        # Показываем текущий характер для справки
        current_traits = profile.get('traits', '').strip() if profile.get('traits') else ''
        if current_traits:
            await query.message.reply_text(
                f"Текущий характер:\n{current_traits}\n\n"
                "Опишите, что вы хотите добавить или изменить в характере.\n\n"
                "Например:\n"
                "- 'Добавь вежливый' - дополнит текущий характер\n"
                "- 'Убери упрямый' - удалит черту из текущего характера"
            )
        else:
            await query.message.reply_text(
                "Опишите черты характера вашего ребенка(детей).\n\n"
                "Например: 'Платон Лидер — умеет вести за собой, вовлекать, договариваться. Демид Создатель миров — способность строить сложные игровые и смысловые конструкции.'"
            )
        context.user_data['waiting_for'] = 'add_traits'
        logger.info(f"Переход в состояние ASKING_TRAITS_ADDITION для пользователя {user_id}")
        return ASKING_TRAITS_ADDITION
    
    elif callback_data == "story_wishes":
        # Обработка пожеланий
        logger.info(f"Пользователь {user_id} выбрал 'Пожелания'")
        
        current_wishes = profile.get('wishes', '').strip() if profile.get('wishes') else ''
        
        if current_wishes:
            # Есть существующие пожелания - предлагаем дополнить или удалить
            keyboard = [
                [InlineKeyboardButton("Дополнить пожелания", callback_data="wishes_add")],
                [InlineKeyboardButton("Удалить пожелания", callback_data="wishes_delete")],
                [InlineKeyboardButton("Отмена", callback_data="wishes_cancel")]
            ]
            await query.message.reply_text(
                f"Текущие пожелания:\n{current_wishes}\n\n"
                "Что вы хотите сделать?",
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            # Нет пожеланий - запрашиваем новые
            await query.message.reply_text(
                "Какие у вас есть дополнительные пожелания? Мы учтем их при написании следующей басни."
            )
            context.user_data['waiting_for'] = 'wishes'
            return ASKING_WISHES
        
        return ConversationHandler.END
    
    elif callback_data == "wishes_add":
        # Дополнить пожелания
        current_wishes = profile.get('wishes', '').strip() if profile.get('wishes') else ''
        if current_wishes:
            await query.message.reply_text(
                f"Текущие пожелания:\n{current_wishes}\n\n"
                "Напишите, что вы хотите добавить к пожеланиям:"
            )
        else:
            await query.message.reply_text(
                "Какие у вас есть дополнительные пожелания? Мы учтем их при написании следующей басни."
            )
        context.user_data['waiting_for'] = 'wishes_edit'
        return ASKING_WISHES_EDIT
    
    elif callback_data == "wishes_delete":
        # Удалить пожелания
        success = update_user_fields(user_id, wishes='')
        if success:
            profile_cache.invalidate(user_id)
            await query.message.reply_text("✅ Пожелания удалены.")
        else:
            await query.message.reply_text("❌ Произошла ошибка при удалении пожеланий.")
        return ConversationHandler.END
    
    elif callback_data == "wishes_cancel":
        # Отмена
        await query.message.reply_text("Отменено.")
        return ConversationHandler.END
    
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




async def handle_wishes(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ответа на вопрос о пожеланиях (первое добавление)."""
    user_id = update.effective_user.id
    wishes = update.message.text.strip()
    
    # Сохраняем пожелания в БД
    success = update_user_fields(user_id, wishes=wishes)
    if not success:
        await update.message.reply_text(
            "Произошла ошибка при сохранении пожеланий. Попробуйте позже."
        )
        return ConversationHandler.END
    
    # Инвалидируем кэш
    profile_cache.invalidate(user_id)
    updated_profile = get_user(user_id)
    if updated_profile:
        profile_cache.set(user_id, updated_profile)
    
    # Проверяем антифлуд перед генерацией
    can_gen, message = antiflood.can_generate(user_id)
    if not can_gen:
        await update.message.reply_text(
            f"✅ Пожелания сохранены! {message}"
        )
        return ConversationHandler.END
    
    # Начинаем генерацию
    antiflood.start_generation(user_id)
    
    try:
        await update.message.reply_text(
            "✅ Пожелания сохранены! ✒️ Пишу басню с учетом ваших пожеланий..."
        )
        # Генерируем басню с учетом пожеланий
        await generate_story_with_wishes(update, context, user_id, updated_profile, wishes)
    finally:
        antiflood.finish_generation(user_id)
    
    return ConversationHandler.END


async def handle_wishes_edit(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ответа на дополнение пожеланий."""
    user_id = update.effective_user.id
    new_wishes_text = update.message.text.strip()
    
    # Получаем текущие пожелания
    profile = profile_cache.get(user_id)
    if not profile:
        profile = get_user(user_id)
        if profile:
            profile_cache.set(user_id, profile)
    
    current_wishes = profile.get('wishes', '').strip() if profile.get('wishes') else ''
    
    # Объединяем текущие и новые пожелания
    if current_wishes:
        updated_wishes = f"{current_wishes}\n{new_wishes_text}"
    else:
        updated_wishes = new_wishes_text
    
    # Сохраняем обновленные пожелания в БД
    success = update_user_fields(user_id, wishes=updated_wishes)
    if not success:
        await update.message.reply_text(
            "Произошла ошибка при сохранении пожеланий. Попробуйте позже."
        )
        return ConversationHandler.END
    
    # Инвалидируем кэш
    profile_cache.invalidate(user_id)
    updated_profile = get_user(user_id)
    if updated_profile:
        profile_cache.set(user_id, updated_profile)
    
    # Проверяем антифлуд перед генерацией
    can_gen, message = antiflood.can_generate(user_id)
    if not can_gen:
        await update.message.reply_text(
            f"✅ Пожелания дополнены! {message}"
        )
        return ConversationHandler.END
    
    # Начинаем генерацию
    antiflood.start_generation(user_id)
    
    try:
        await update.message.reply_text(
            "✅ Пожелания дополнены! ✒️ Пишу басню с учетом ваших пожеланий..."
        )
        # Генерируем басню с учетом обновленных пожеланий
        await generate_story_with_wishes(update, context, user_id, updated_profile, updated_wishes)
    finally:
        antiflood.finish_generation(user_id)
    
    return ConversationHandler.END


async def handle_traits_addition(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ответа на вопрос о дополнении/изменении характера."""
    user_id = update.effective_user.id
    logger.info(f"Получен ответ на изменение характера от пользователя {user_id}")
    user_message = update.message.text.strip()
    
    # Отправляем статусное сообщение сразу же
    status_msg = await update.message.reply_text("✒️ Пишу басню с учетом изменений в характере...")
    
    # Получаем текущий профиль
    profile = profile_cache.get(user_id)
    if not profile:
        profile = get_user(user_id)
        if profile:
            profile_cache.set(user_id, profile)
    
    if not profile:
        await status_msg.edit_text(
            "Произошла ошибка при загрузке профиля. Попробуйте позже."
        )
        return ConversationHandler.END
    
    # Используем агента для анализа намерения пользователя
    # Агент определит: удалить, заменить, дополнить или удалить частично
    # Передаем флаг is_add_traits_request=True, так как пользователь нажал кнопку "Дополнить характер"
    try:
        agent_response = agent_router.process_message(user_message, profile, is_add_traits_request=True)
        logger.info(f"Agent 1 обработал запрос на изменение характера для пользователя {user_id}")
    except Exception as e:
        logger.error(f"Ошибка при вызове Agent 1 для изменения характера: {e}", exc_info=True)
        await status_msg.edit_text(
            "❌ Ошибка при обработке запроса. Попробуйте позже."
        )
        return ConversationHandler.END
    
    # Обновляем профиль, если агент определил, что нужно обновить
    if agent_response.get("should_update_profile", False):
        profile_patch = agent_response.get("profile_patch", {})
        if profile_patch and "traits" in profile_patch:
            # Обновляем traits в БД (может быть пустой строкой для удаления)
            success = update_user_fields(user_id, traits=profile_patch["traits"])
            if not success:
                await status_msg.edit_text(
                    "Произошла ошибка при сохранении. Попробуйте позже."
                )
                return ConversationHandler.END
            
            # Инвалидируем кэш и обновляем
            profile_cache.invalidate(user_id)
            updated_profile = get_user(user_id)
            if updated_profile:
                profile_cache.set(user_id, updated_profile)
                profile = updated_profile
        else:
            logger.warning(f"Agent вернул should_update_profile=True, но traits отсутствует в profile_patch для пользователя {user_id}")
    else:
        logger.info(f"Agent определил, что обновление профиля не требуется для пользователя {user_id}")
    
    # Генерируем басню с обновленным характером
    await generate_story_with_updated_traits(update, context, user_id, profile, user_message, status_msg)
    
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
        
        # Сохраняем выбранную мораль в context_active
        if "moral" in agent_response:
            moral = agent_response["moral"]
            logger.info(f"Получена мораль для сохранения в context_active для пользователя {user_id}: {moral}")
            success = update_user_fields(user_id, context_active=moral)
            if success:
                # Инвалидируем кэш и обновляем профиль
                profile_cache.invalidate(user_id)
                updated_profile = get_user(user_id)
                if updated_profile:
                    profile_cache.set(user_id, updated_profile)
                    profile = updated_profile
                    logger.info(f"Сохранена случайная мораль в context_active для пользователя {user_id}: {moral}. Новый context_active: {updated_profile.get('context_active', 'не найден')}")
                else:
                    logger.warning(f"Не удалось получить обновленный профиль для пользователя {user_id}")
            else:
                logger.warning(f"Не удалось сохранить мораль в context_active для пользователя {user_id}")
        else:
            logger.error(f"В ответе agent_router отсутствует поле 'moral' для пользователя {user_id}. Ответ: {agent_response}")
        
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


async def generate_story_with_wishes(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    profile: Dict,
    wishes: str
):
    """Генерирует басню с учетом пожеланий."""
    try:
        # Используем агент-роутер для формирования промпта
        # Передаем пожелания как user_message, чтобы агент учел их
        agent_response = agent_router.process_story_request(
            request_type="wishes",
            user_message=f"Учти следующие пожелания при написании басни: {wishes}",
            user_profile=profile
        )
        
        await generate_and_send_story_internal(update, context, user_id, profile, agent_response)
    except Exception as e:
        logger.error(f"Ошибка при генерации басни с пожеланиями: {e}", exc_info=True)
        message_target = update.message if update.message else (update.callback_query.message if update.callback_query else None)
        if message_target:
            await message_target.reply_text(
                "❌ Произошла ошибка при генерации басни. Попробуйте позже."
            )


async def generate_story_with_updated_traits(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    profile: Dict,
    user_message: str = "",
    status_msg = None
):
    """Генерирует басню с обновленным характером."""
    try:
        # Используем агент-роутер для формирования промпта
        agent_response = agent_router.process_story_request(
            request_type="add_traits",
            user_message=user_message,
            user_profile=profile
        )
        
        await generate_and_send_story_internal(update, context, user_id, profile, agent_response, status_msg)
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
    agent_response: Dict,
    status_msg = None
):
    """Внутренняя функция для генерации и отправки басни.
    
    Args:
        status_msg: Опциональное статус-сообщение, которое будет удалено после успешной генерации басни.
    """
    message_target = update.message if update.message else (update.callback_query.message if update.callback_query else None)
    
    try:
        # Определяем, откуда отправлять сообщения
        if not message_target:
            logger.error(f"Не удалось определить target для отправки сообщения для пользователя {user_id}")
            return
        
        # Проверяем, что agent_response не пустой
        if not agent_response:
            logger.error(f"Пустой agent_response для пользователя {user_id}")
            if status_msg:
                try:
                    await status_msg.edit_text(
                        "❌ Ошибка при формировании запроса. Попробуйте позже."
                    )
                except Exception as edit_error:
                    logger.warning(f"Не удалось обновить статус-сообщение: {edit_error}")
                    await message_target.reply_text(
                        "❌ Ошибка при формировании запроса. Попробуйте позже."
                    )
            else:
                await message_target.reply_text(
                    "❌ Ошибка при формировании запроса. Попробуйте позже."
                )
            return
        
        # Генерируем басню через DeepSeek
        deepseek_prompt = agent_response.get("deepseek_user_prompt", "")
        if not deepseek_prompt:
            logger.error(f"Пустой промпт от Agent 1 для пользователя {user_id}, agent_response: {agent_response}")
            if status_msg:
                try:
                    await status_msg.edit_text(
                        "❌ Ошибка при формировании запроса. Попробуйте позже."
                    )
                except Exception as edit_error:
                    logger.warning(f"Не удалось обновить статус-сообщение: {edit_error}")
                    await message_target.reply_text(
                        "❌ Ошибка при формировании запроса. Попробуйте позже."
                    )
            else:
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
            wishes = profile.get('wishes', '').strip() if profile.get('wishes') else ''
            request_type = agent_response.get("request_type", "regular")
            story_total = profile.get('story_total', 0) or 0
            is_first_story = (story_total == 0)
            
            profile_header = f"ГЛАВНЫЕ ГЕРОИ басни (обязательно используй их в басне):\n"
            profile_header += f"- Имена: {child_names}\n"
            
            # Возраст и черты характера всегда учитываются, но не прописываются текстом
            if age:
                profile_header += f"- Возраст: {age} (УЧИТЫВАЙ при написании: сложность языка, понятность сюжета, глубину морали - но НЕ пиши возраст текстом в басне)\n"
            if traits:
                profile_header += f"- Черты характера: {traits} (ОБЯЗАТЕЛЬНО отрази в поведении и поступках героя, но СТРОГО ЗАПРЕЩЕНО упоминать их текстом. НЕ используй конструкции типа 'сказал он конструктор', 'он наставник', 'он генератор идей' и т.д. Покажи характер только через действия)\n"
            
            # Для случайной морали НЕ добавляем context_active
            if request_type != "random_moral" and context_active:
                profile_header += f"\nВАЖНО - РЕАЛЬНАЯ СИТУАЦИЯ ДЛЯ РАЗБОРА:\n{context_active}\n"
                profile_header += "Басня ОБЯЗАТЕЛЬНО должна разбирать именно эту ситуацию. Мораль НЕ должна быть написана текстом - она должна быть понятна из действий и выбора героя.\n"
            
            # Добавляем пожелания, если они есть
            if wishes:
                profile_header += f"\nДОПОЛНИТЕЛЬНЫЕ ПОЖЕЛАНИЯ (ОБЯЗАТЕЛЬНО УЧТИ):\n{wishes}\n"
                profile_header += "Эти пожелания должны быть учтены при написании басни.\n"
            
            profile_header += f"\nЗАДАНИЕ: {deepseek_prompt}\n\n"
            
            # Финальное напоминание всегда включает инструкции по возрасту и характеру
            profile_header += "ВАЖНО: Главными героями басни ДОЛЖНЫ быть именно эти дети с указанными именами. "
            if age or traits:
                profile_header += "Обязательно учитывай возраст и черты характера при написании (сложность языка, поведение героя), но СТРОГО ЗАПРЕЩЕНО писать их текстом. НЕ используй роли или типы личности типа 'конструктор', 'наставник', 'генератор идей' и т.д."
            
            deepseek_prompt = profile_header
            
            logger.info(f"Добавлена информация о детях в промпт: {child_names}")
            if request_type != "random_moral" and context_active:
                logger.info(f"Добавлен контекст ситуации: {context_active[:100]}...")
            if wishes:
                logger.info(f"Добавлены пожелания: {wishes[:100]}...")
        else:
            logger.warning(f"Профиль не найден или некорректен для пользователя {user_id}, используем базовый промпт")
        
        logger.info(f"Генерирую басню через DeepSeek для пользователя {user_id}, длина промпта: {len(deepseek_prompt)}")
        story_text = deepseek_client.generate_story(deepseek_prompt)
        
        if not story_text:
            logger.error(f"DeepSeek вернул пустой ответ для пользователя {user_id}")
            # Если есть статус-сообщение, обновляем его
            if status_msg:
                try:
                    await status_msg.edit_text(
                        "❌ Произошла ошибка при генерации басни. Попробуйте позже."
                    )
                except Exception as edit_error:
                    logger.warning(f"Не удалось обновить статус-сообщение: {edit_error}")
                    await message_target.reply_text(
                        "❌ Произошла ошибка при генерации басни. Попробуйте позже."
                    )
            else:
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
        
        # Удаляем статус-сообщение, если оно было передано (перед отправкой басни)
        if status_msg:
            try:
                await status_msg.delete()
            except Exception as e:
                logger.warning(f"Не удалось удалить статус-сообщение: {e}")
        
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
        # Если произошла ошибка, обновляем статус-сообщение вместо удаления
        if status_msg:
            try:
                await status_msg.edit_text(
                    "❌ Произошла ошибка при генерации басни. Попробуйте позже."
                )
            except Exception as edit_error:
                logger.warning(f"Не удалось обновить статус-сообщение: {edit_error}")
                if message_target:
                    try:
                        await message_target.reply_text(
                            "❌ Произошла ошибка при генерации басни. Попробуйте позже."
                        )
                    except Exception as send_error:
                        logger.error(f"Ошибка при отправке сообщения об ошибке пользователю {user_id}: {send_error}", exc_info=True)
        elif message_target:
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
        
        # Используем внутреннюю функцию для генерации (передаем status_msg, чтобы оно удалилось после генерации)
        agent_response['request_type'] = 'regular'  # Обычный запрос
        await generate_and_send_story_internal(update, context, user_id, profile, agent_response, status_msg)
        
    except Exception as e:
        logger.error(f"Ошибка при генерации басни для пользователя {user_id}: {e}", exc_info=True)
        try:
            if 'status_msg' in locals():
                await status_msg.edit_text(
                    "❌ Произошла ошибка при генерации басни. Попробуйте позже."
                )
            else:
                await update.message.reply_text(
                    "❌ Произошла ошибка при генерации басни. Попробуйте позже."
                )
        except:
            await update.message.reply_text(
                "❌ Произошла ошибка при генерации басни. Попробуйте позже."
            )


def main():
    """Запуск бота."""
    logger.info("Запуск бота 'Баснописец'...")
    
    # Проверяем и применяем миграцию для колонки wishes, если нужно
    try:
        from db.session import engine  # noqa
        from sqlalchemy import text, inspect  # noqa
        
        inspector = inspect(engine)
        columns = [col['name'] for col in inspector.get_columns('users')]
        
        if 'wishes' not in columns:
            logger.warning("Колонка 'wishes' отсутствует в БД. Пытаюсь добавить...")
            try:
                with engine.connect() as conn:
                    conn.execute(text("ALTER TABLE users ADD COLUMN wishes TEXT"))
                    conn.commit()
                logger.info("✓ Колонка 'wishes' успешно добавлена в БД")
            except Exception as e:
                logger.error(f"Не удалось добавить колонку 'wishes': {e}")
                logger.error("Пожалуйста, примените миграцию вручную: python check_and_fix_wishes.py")
        else:
            logger.info("✓ Колонка 'wishes' присутствует в БД")
    except Exception as e:
        logger.warning(f"Не удалось проверить структуру БД: {e}")
        logger.warning("Продолжаю запуск, но возможны ошибки при сохранении профилей")
    
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
        entry_points=[CallbackQueryHandler(handle_story_callback, pattern="^(story_|wishes_)")],
        states={
            ASKING_NEW_DILEMMA: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_new_dilemma)],
            ASKING_TRAITS_ADDITION: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_traits_addition)],
            ASKING_WISHES: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wishes)],
            ASKING_WISHES_EDIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, handle_wishes_edit)],
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

