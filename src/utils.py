"""Утилиты: антифлуд, кэш профиля, разбиение сообщений."""
import time
import logging
from typing import Dict, Optional, Any, Tuple, List
from datetime import datetime, timedelta

logger = logging.getLogger(__name__)


class AntifloodManager:
    """Менеджер антифлуда: не чаще 1 генерации/15 секунд на пользователя."""
    
    def __init__(self, cooldown_seconds: int = 15):
        self.cooldown_seconds = cooldown_seconds
        self.last_generation: Dict[int, float] = {}
        self.generating: Dict[int, bool] = {}
    
    def can_generate(self, user_id: int) -> Tuple[bool, Optional[str]]:
        """
        Проверяет, можно ли генерировать для пользователя.
        Возвращает (можно_ли, сообщение_если_нет).
        """
        now = time.time()
        
        # Если уже генерируется
        if self.generating.get(user_id, False):
            return False, "Принял, генерирую — подождите…"
        
        # Проверяем кулдаун
        last_time = self.last_generation.get(user_id, 0)
        elapsed = now - last_time
        
        if elapsed < self.cooldown_seconds:
            remaining = int(self.cooldown_seconds - elapsed)
            return False, f"Подождите {remaining} секунд перед следующей генерацией."
        
        return True, None
    
    def start_generation(self, user_id: int):
        """Отмечает начало генерации."""
        self.generating[user_id] = True
    
    def finish_generation(self, user_id: int):
        """Отмечает завершение генерации и обновляет время."""
        self.generating[user_id] = False
        self.last_generation[user_id] = time.time()


class ProfileCache:
    """Кэш профилей пользователей с TTL."""
    
    def __init__(self, ttl_minutes: int = 5):
        self.ttl_minutes = ttl_minutes
        self.cache: Dict[int, Tuple[Dict[str, Any], datetime]] = {}
    
    def get(self, user_id: int) -> Optional[Dict[str, Any]]:
        """Получает профиль из кэша, если он не устарел."""
        if user_id not in self.cache:
            return None
        
        profile, cached_at = self.cache[user_id]
        if datetime.now() - cached_at > timedelta(minutes=self.ttl_minutes):
            del self.cache[user_id]
            return None
        
        return profile
    
    def set(self, user_id: int, profile: Dict[str, Any]):
        """Сохраняет профиль в кэш."""
        self.cache[user_id] = (profile, datetime.now())
    
    def invalidate(self, user_id: int):
        """Удаляет профиль из кэша."""
        if user_id in self.cache:
            del self.cache[user_id]


def split_message(text: str, max_length: int = 3800) -> List[str]:
    """
    Разбивает длинное сообщение на части по ~3800 символов.
    Старается разбивать по предложениям.
    """
    if len(text) <= max_length:
        return [text]
    
    chunks = []
    current_chunk = ""
    
    # Разбиваем по предложениям (точка, восклицательный, вопросительный знак + пробел)
    sentences = []
    buffer = ""
    
    for char in text:
        buffer += char
        if char in ".!?" and len(buffer) > 10:  # Минимальная длина предложения
            sentences.append(buffer)
            buffer = ""
    
    if buffer:
        sentences.append(buffer)
    
    # Если предложений нет или они слишком длинные, разбиваем по абзацам
    if not sentences or any(len(s) > max_length for s in sentences):
        sentences = text.split("\n\n")
        if not sentences:
            sentences = [text]
    
    # Формируем чанки
    for sentence in sentences:
        if len(current_chunk) + len(sentence) <= max_length:
            current_chunk += sentence
        else:
            if current_chunk:
                chunks.append(current_chunk.strip())
            # Если предложение само по себе длиннее max_length, разбиваем принудительно
            if len(sentence) > max_length:
                for i in range(0, len(sentence), max_length):
                    chunks.append(sentence[i:i + max_length])
                current_chunk = ""
            else:
                current_chunk = sentence
    
    if current_chunk:
        chunks.append(current_chunk.strip())
    
    return chunks if chunks else [text]

