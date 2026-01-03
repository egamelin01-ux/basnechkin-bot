"""Клиент для работы с DeepSeek API - генерация басен."""
import logging
import requests
from typing import Optional

from config import DEEPSEEK_API_KEY, DEEPSEEK_API_URL

logger = logging.getLogger(__name__)


class DeepSeekClient:
    """Клиент для генерации басен через DeepSeek API."""
    
    def __init__(self):
        self.api_key = DEEPSEEK_API_KEY
        self.api_url = DEEPSEEK_API_URL
    
    def generate_story(self, user_prompt: str) -> Optional[str]:
        """
        Генерирует басню через DeepSeek API.
        
        Args:
            user_prompt: Промпт от Agent 1 для генерации басни
        
        Returns:
            Текст басни или None в случае ошибки
        """
        try:
            system_prompt = """Ты — талантливый автор басен по мотивам басен Ивана Андреевича Крылова. 

Твоя задача — создавать поучительные басни, в которых главными героями становятся КОНКРЕТНЫЕ дети, описанные в запросе.

КРИТИЧЕСКИ ВАЖНО:
- Если в запросе указаны конкретные имена детей (например, "Платон", "Демид") — ОБЯЗАТЕЛЬНО используй именно эти имена
- Если указаны черты характера — ОБЯЗАТЕЛЬНО отрази их в поведении персонажей
- НЕ придумывай случайных имен или персонажей вместо указанных детей
- Главные герои басни — это РЕАЛЬНЫЕ дети из запроса, не выдуманные персонажи

Требования:
- Стиль должен быть похож на стиль Крылова
- Басня должна быть поучительной и понятной для детей
- В конце должна быть мораль
- Длина: 500-900 слов
- Язык: русский
- Не используй мат и контент 18+
- Используй ТОЧНЫЕ имена детей из запроса, не заменяй их на другие"""

            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key}"
            }
            
            payload = {
                "model": "deepseek-chat",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_prompt}
                ],
                "temperature": 0.8,
                "max_tokens": 2000,
                "stream": False
            }
            
            logger.info(f"Отправляю запрос к DeepSeek API: {self.api_url}")
            
            response = requests.post(
                self.api_url,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            # Проверяем статус ответа
            if response.status_code != 200:
                error_data = {}
                try:
                    error_data = response.json()
                except:
                    error_data = {"error": response.text[:500]}
                
                error_msg = error_data.get("error", {})
                if isinstance(error_msg, dict):
                    error_message = error_msg.get("message", str(error_data))
                else:
                    error_message = str(error_data)
                
                # Специальная обработка для ошибки баланса
                if response.status_code == 402 or "balance" in error_message.lower() or "insufficient" in error_message.lower():
                    logger.error(f"DeepSeek API: Недостаточно баланса на счету. {error_message}")
                else:
                    logger.error(f"DeepSeek API вернул ошибку {response.status_code}: {error_message}")
                return None
            
            data = response.json()
            
            # Извлекаем текст басни
            if "choices" in data and len(data["choices"]) > 0:
                story_text = data["choices"][0]["message"]["content"]
                logger.info("Басня успешно сгенерирована через DeepSeek")
                return story_text
            else:
                logger.error(f"DeepSeek вернул неожиданный формат ответа: {data}")
                return None
                
        except requests.exceptions.HTTPError as e:
            error_detail = ""
            try:
                if hasattr(e, 'response') and e.response is not None:
                    error_data = e.response.json()
                    error_detail = f" Response: {error_data}"
                else:
                    error_detail = f" Status: {e}"
            except:
                error_detail = f" Error: {str(e)}"
            logger.error(f"HTTP ошибка при запросе к DeepSeek API: {e}{error_detail}")
            return None
        except requests.exceptions.RequestException as e:
            logger.error(f"Ошибка запроса к DeepSeek API: {e}")
            return None
        except Exception as e:
            logger.error(f"Ошибка генерации басни: {e}", exc_info=True)
            return None

