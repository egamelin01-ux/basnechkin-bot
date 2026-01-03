"""Основной файл Telegram-бота 'Баснечкин'."""
import logging
from typing import Dict

from telegram import Update
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    filters,
    ContextTypes
)

from config import TELEGRAM_BOT_TOKEN
from sheets import GoogleSheetsClient
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
ASKING_NAME, ASKING_AGE, ASKING_TRAITS = range(3)

# Инициализация компонентов
sheets_client = GoogleSheetsClient()
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
    profile = sheets_client.get_user_profile(user_id)
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
        "чтобы в наших баснях главными героями были бы ваши дети."
    )
    
    # Начинаем анкету
    await update.message.reply_text("Как зовут вашего ребенка (детей)?")
    
    return ASKING_NAME


async def handle_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработчик ответа на вопрос об имени."""
    child_names = update.message.text.strip()
    context.user_data['child_names'] = child_names
    
    await update.message.reply_text("Сколько лет?")
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
    
    success = sheets_client.create_user_profile(
        user_id=user_id,
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
    
    # Отправляем подтверждение
    await update.message.reply_text(
        "✅ Спасибо! Профиль сохранен. Сейчас я сгенерирую для вас первую басню-знакомство."
    )
    
    # Загружаем профиль для Agent 1
    profile = sheets_client.get_user_profile(user_id)
    profile_cache.set(user_id, profile)
    
    # Генерируем первую басню автоматически
    await generate_and_send_story(update, context, "Напиши первую басню-знакомство с ребенком.")
    
    return ConversationHandler.END


async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Отмена анкеты."""
    await update.message.reply_text("Анкета отменена. Используйте /start для начала.")
    return ConversationHandler.END


async def reset_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Команда /reset - сброс профиля и начало заново."""
    user_id = update.effective_user.id
    
    # Проверяем, есть ли профиль
    profile = sheets_client.get_user_profile(user_id)
    if not profile:
        await update.message.reply_text(
            "У вас нет сохраненного профиля. Используйте /start для регистрации."
        )
        return
    
    # Удаляем профиль и все басни
    success = sheets_client.delete_user_profile(user_id)
    
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
    
    logger.info(f"Пользователь {user_id} отправил сообщение: {user_message[:50]}...")
    
    # Проверяем наличие профиля
    profile = profile_cache.get(user_id)
    if not profile:
        profile = sheets_client.get_user_profile(user_id)
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


async def generate_and_send_story(
    update: Update,
    context: ContextTypes.DEFAULT_TYPE,
    user_message: str
):
    """Генерирует басню и отправляет пользователю."""
    user_id = update.effective_user.id
    
    try:
        # Загружаем профиль (из кэша или из Sheets)
        profile = profile_cache.get(user_id)
        if not profile:
            profile = sheets_client.get_user_profile(user_id)
            if profile:
                profile_cache.set(user_id, profile)
        
        if not profile:
            await update.message.reply_text(
                "Произошла ошибка при загрузке профиля. Используйте /start для повторной регистрации."
            )
            return
        
        # Отправляем индикатор генерации
        status_msg = await update.message.reply_text("🔄 Генерирую басню...")
        
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
                # Добавляем last_user_message в patch, если его нет
                if "last_user_message" not in profile_patch:
                    profile_patch["last_user_message"] = user_message
                
                success = sheets_client.update_user_profile(user_id, profile_patch)
                if success:
                    # Инвалидируем кэш и обновляем
                    profile_cache.invalidate(user_id)
                    updated_profile = sheets_client.get_user_profile(user_id)
                    if updated_profile:
                        profile_cache.set(user_id, updated_profile)
                        profile = updated_profile
        
        # Генерируем басню через DeepSeek
        deepseek_prompt = agent_response.get("deepseek_user_prompt", "")
        if not deepseek_prompt:
            logger.error(f"Пустой промпт от Agent 1 для пользователя {user_id}")
            await status_msg.edit_text(
                "❌ Ошибка при формировании запроса. Попробуйте позже."
            )
            return
        
        # ВАЖНО: Добавляем информацию о детях из профиля в начало промпта
        # Это гарантирует, что DeepSeek всегда будет использовать реальные данные
        if profile:
            child_names = profile.get('child_names', '').strip()
            age = profile.get('age', '').strip()
            traits = profile.get('traits', '').strip()
            
            if child_names:
                profile_header = f"ГЛАВНЫЕ ГЕРОИ БАСНИ (обязательно используй их в басне):\n"
                profile_header += f"- Имена: {child_names}\n"
                if age:
                    profile_header += f"- Возраст: {age}\n"
                if traits:
                    profile_header += f"- Черты характера: {traits}\n"
                profile_header += f"\nЗАДАНИЕ: {deepseek_prompt}\n\n"
                profile_header += "ВАЖНО: Главными героями басни ДОЛЖНЫ быть именно эти дети с указанными именами и чертами характера. Не придумывай других персонажей."
                
                deepseek_prompt = profile_header
                logger.info(f"Добавлена информация о детях в промпт: {child_names}")
        
        logger.info(f"Генерирую басню через DeepSeek для пользователя {user_id}, длина промпта: {len(deepseek_prompt)}")
        story_text = deepseek_client.generate_story(deepseek_prompt)
        
        if not story_text:
            await status_msg.edit_text(
                "❌ Произошла ошибка при генерации басни. Попробуйте позже."
            )
            return
        
        # Удаляем статус-сообщение
        await status_msg.delete()
        
        # Сохраняем басню в Sheets (trim выполнится автоматически)
        sheets_client.save_story(user_id, story_text, model='deepseek')
        
        # Отправляем басню частями, если она длинная
        chunks = split_message(story_text)
        for i, chunk in enumerate(chunks):
            if i == 0:
                await update.message.reply_text(chunk)
            else:
                await update.message.reply_text(chunk)
        
        logger.info(f"Басня успешно отправлена пользователю {user_id}")
        
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
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )
    
    # Регистрируем обработчики
    application.add_handler(CommandHandler("reset", reset_command))
    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    
    # Запускаем бота
    logger.info("Бот запущен и готов к работе")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    main()

