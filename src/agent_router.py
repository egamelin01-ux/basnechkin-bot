"""Agent 1 (OpenAI) - роутер логики и генератор промптов для DeepSeek."""
import json
import logging
import random
from typing import Dict, Any, Optional
from openai import OpenAI

from config import OPENAI_API_KEY

logger = logging.getLogger(__name__)

# Список моралей для разных возрастов
MORALS_BY_AGE = {
    "3-5": [
        "Дружба важнее игрушек",
        "Нужно делиться с друзьями",
        "Слушаться родителей - это хорошо",
        "Быть добрым к другим",
        "Не нужно жадничать",
        "Помогать другим - это хорошо",
        "Не нужно драться",
        "Быть вежливым",
    ],
    "6-8": [
        "Честность - лучшая политика",
        "Трудолюбие приводит к успеху",
        "Не суди других по внешности",
        "Важно быть ответственным",
        "Упорство помогает достичь цели",
        "Скромность украшает человека",
        "Не нужно хвастаться",
        "Важно уважать старших",
    ],
    "9-12": [
        "Справедливость важнее личной выгоды",
        "Знания - это сила",
        "Не нужно завидовать другим",
        "Важно быть терпеливым",
        "Самоконтроль - признак зрелости",
        "Важно уметь прощать",
        "Не нужно лгать",
        "Важно быть благодарным",
    ],
    "13+": [
        "Честь и достоинство важнее выгоды",
        "Мудрость приходит с опытом",
        "Важно быть верным своим принципам",
        "Не нужно предавать друзей",
        "Самопознание - путь к мудрости",
        "Важно уметь признавать ошибки",
        "Справедливость превыше всего",
        "Важно быть милосердным",
    ],
}


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
- deepseek_user_prompt: на русском языке, стиль басни по мотивам Крылова, не в стихах, мораль в конце, 800-900 слов, учитывай профиль ребенка(детей) + запрос пользователя. 
- Не проси писать про возраст детей, но проси учитывать возраст при написании сказки и в зависимости от возраста регулируй сложность контекста, литературных выражений и морали.
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
    
    def get_random_moral_by_age(self, age: str) -> str:
        """Получает случайную мораль на основе возраста."""
        # Определяем возрастную группу
        age_str = str(age).strip().lower()
        age_group = None
        
        # Пытаемся извлечь число из возраста
        try:
            age_num = int(''.join(filter(str.isdigit, age_str)))
            if age_num <= 5:
                age_group = "3-5"
            elif age_num <= 8:
                age_group = "6-8"
            elif age_num <= 12:
                age_group = "9-12"
            else:
                age_group = "13+"
        except:
            # Если не удалось определить, используем среднюю группу
            age_group = "6-8"
        
        morals = MORALS_BY_AGE.get(age_group, MORALS_BY_AGE["6-8"])
        return random.choice(morals)
    
    def process_story_request(
        self,
        request_type: str,
        user_message: str,
        user_profile: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Обрабатывает специальные запросы на генерацию басни.
        
        request_type может быть:
        - "new_dilemma": новая дилемма (обновляет context_active)
        - "random_moral": случайная мораль (не использует context_active)
        - "previous_moral": прошлая мораль (использует context_active)
        - "add_traits": дополнить характер (обновляет traits)
        - "regular": обычный запрос
        
        Возвращает:
        {
            "request_type": str,
            "deepseek_user_prompt": "string"
        }
        """
        try:
            age = user_profile.get('age', '') if user_profile else ''
            
            if request_type == "new_dilemma":
                # Новая дилемма - формируем промпт на основе новой ситуации
                prompt = f"Напиши басню по мотивам Крылова, которая разбирает следующую ситуацию: {user_message}. " \
                        f"Басня должна иметь явную мораль в конце, которая помогает ребенку понять, как правильно поступать в такой ситуации."
                return {
                    "request_type": "new_dilemma",
                    "deepseek_user_prompt": prompt
                }
            
            elif request_type == "random_moral":
                # Случайная мораль - генерируем мораль на основе возраста
                try:
                    moral = self.get_random_moral_by_age(age)
                    prompt = f"Напиши басню по мотивам Крылова со следующей моралью: {moral}. " \
                            f"Басня должна быть интересной и поучительной, с явной моралью в конце."
                    logger.info(f"Сгенерирована случайная мораль для возраста {age}: {moral}")
                    return {
                        "request_type": "random_moral",
                        "deepseek_user_prompt": prompt
                    }
                except Exception as e:
                    logger.error(f"Ошибка при генерации случайной морали для возраста {age}: {e}", exc_info=True)
                    # Возвращаем дефолтную мораль
                    default_moral = "Дружба важнее игрушек"
                    prompt = f"Напиши басню по мотивам Крылова со следующей моралью: {default_moral}. " \
                            f"Басня должна быть интересной и поучительной, с явной моралью в конце."
                    return {
                        "request_type": "random_moral",
                        "deepseek_user_prompt": prompt
                    }
            
            elif request_type == "previous_moral":
                # Прошлая мораль - используем context_active
                prompt = f"Напиши басню по мотивам Крылова, которая разбирает следующую ситуацию: {user_message}. " \
                        f"Басня должна иметь явную мораль в конце, которая помогает ребенку понять, как правильно поступать в такой ситуации."
                return {
                    "request_type": "previous_moral",
                    "deepseek_user_prompt": prompt
                }
            
            elif request_type == "add_traits":
                # Дополнить характер - просто генерируем обычную басню
                prompt = "Напиши басню по мотивам Крылова, которая учитывает обновленные черты характера ребенка. " \
                        f"Басня должна быть интересной и поучительной, с явной моралью в конце."
                return {
                    "request_type": "add_traits",
                    "deepseek_user_prompt": prompt
                }
            
            else:
                # Обычный запрос
                prompt = f"Напиши басню по мотивам Крылова на основе запроса: {user_message}"
                return {
                    "request_type": "regular",
                    "deepseek_user_prompt": prompt
                }
                
        except Exception as e:
            logger.error(f"Ошибка в process_story_request: {e}")
            return {
                "request_type": request_type,
                "deepseek_user_prompt": f"Напиши басню по мотивам Крылова."
            }

