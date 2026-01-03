"""Agent 1 (OpenAI) - роутер логики и генератор промптов для DeepSeek."""
import json
import logging
from typing import Dict, Any, Optional
from openai import OpenAI

from config import OPENAI_API_KEY

logger = logging.getLogger(__name__)


class AgentRouter:
    """Agent 1: анализирует сообщения и формирует промпты для DeepSeek."""
    
    def __init__(self):
        self.client = OpenAI(api_key=OPENAI_API_KEY)
    
    def process_message(
        self,
        user_message: str,
        user_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Обрабатывает сообщение пользователя и возвращает JSON-ответ.
        
        Возвращает:
        {
            "should_update_profile": bool,
            "profile_patch": {
                "child_names": "string_optional",
                "age": "string_optional",
                "traits": "string_optional",
                "last_user_message": "string_optional"
            },
            "deepseek_user_prompt": "string"
        }
        """
        try:
            # Формируем системный промпт для Agent 1
            system_prompt = """Ты — интеллектуальный роутер для бота "Баснечкин", который помогает родителям наставлять детей через басни по мотивам Крылова.

Твоя задача:
1. Анализировать сообщения пользователя
2. Определять, нужно ли обновлять профиль ребенка (имя, возраст, черты характера)
3. Формировать промпт для генерации басни

ПРАВИЛА:
- Если пользователь корректирует профиль ("ему 6, а не 5", "он не спокойный, а упрямый", "двое детей: Маша и Петя") → should_update_profile=true и заполни profile_patch
- Если запрос просто "напиши сказку про..." или обычный запрос басни → should_update_profile=false
- deepseek_user_prompt: на русском языке, стиль басни по мотивам Крылова, мораль в конце, 500-900 слов, учитывай профиль ребенка(детей) + запрос пользователя
- НЕ используй мат и контент 18+

ВАЖНО: Возвращай ТОЛЬКО валидный JSON без пояснений и комментариев."""

            # Формируем промпт пользователя
            profile_info = ""
            if user_profile:
                profile_info = f"""
Профиль ребенка:
- Имя: {user_profile.get('child_names', 'не указано')}
- Возраст: {user_profile.get('age', 'не указан')}
- Черты характера: {user_profile.get('traits', 'не указаны')}
"""
            
            user_prompt = f"""Сообщение пользователя: {user_message}
{profile_info}

Верни JSON в следующем формате:
{{
    "should_update_profile": true/false,
    "profile_patch": {{
        "child_names": "string или null",
        "age": "string или null",
        "traits": "string или null",
        "last_user_message": "string или null"
    }},
    "deepseek_user_prompt": "полный промпт для генерации басни на русском языке"
}}"""

            # Вызываем OpenAI
            response = self.client.chat.completions.create(
                model="gpt-4o-mini",
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                temperature=0.7,
                response_format={"type": "json_object"}
            )
            
            # Парсим JSON-ответ
            content = response.choices[0].message.content
            result = json.loads(content)
            
            # Валидация и нормализация
            if "should_update_profile" not in result:
                result["should_update_profile"] = False
            
            if "profile_patch" not in result:
                result["profile_patch"] = {}
            
            if "deepseek_user_prompt" not in result:
                result["deepseek_user_prompt"] = "Напиши басню по мотивам Крылова."
            
            # Убираем null значения из profile_patch
            profile_patch = {}
            for key in ["child_names", "age", "traits", "last_user_message"]:
                if key in result["profile_patch"] and result["profile_patch"][key] is not None:
                    profile_patch[key] = str(result["profile_patch"][key])
            
            result["profile_patch"] = profile_patch
            
            logger.info(f"Agent 1 обработал сообщение: should_update={result['should_update_profile']}")
            return result
            
        except json.JSONDecodeError as e:
            logger.error(f"Ошибка парсинга JSON от Agent 1: {e}")
            # Возвращаем дефолтный ответ
            return {
                "should_update_profile": False,
                "profile_patch": {},
                "deepseek_user_prompt": f"Напиши басню по мотивам Крылова на основе запроса: {user_message}"
            }
        except Exception as e:
            logger.error(f"Ошибка вызова Agent 1: {e}")
            # Возвращаем дефолтный ответ
            return {
                "should_update_profile": False,
                "profile_patch": {},
                "deepseek_user_prompt": f"Напиши басню по мотивам Крылова на основе запроса: {user_message}"
            }

