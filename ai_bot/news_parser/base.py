"""Базовый класс для парсеров новостей с общей логикой фильтрации."""

import re
import logging
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional, List

logger = logging.getLogger(__name__)


class BaseParser(ABC):
    """Базовый класс для всех парсеров новостей с общей логикой фильтрации."""
    
    # Общие ключевые слова рекламы для всех парсеров
    AD_KEYWORDS = [
        # Прямые указания на рекламу
        'реклама', 'спонсор', 'партнер', 'анонс', 'pr ', 'pr:', 'pr-',
        'спонсорский', 'партнерский', 'коммерческий', 'маркетинг',
        # Хэштеги
        '#ad', '#sponsored', '#реклама', '#спонсор', '#анонс',
        '#pr', '#partner', '#commercial',
        # Коммерческие слова
        'купить', 'цена', 'скидка', 'акция', 'распродажа', 'товар',
        'заказать', 'доставка', 'оплата', 'рублей', 'руб.',
        # Призывы к действию (часто в рекламе)
        'пишите в лс', 'писать в лс', 'в личные сообщения',
        'подробнее в профиле', 'ссылка в био',
    ]
    
    # Паттерны контактной информации
    CONTACT_PATTERNS = [
        r'@\w+',  # Telegram username
        r'\+?\d{10,}',  # Телефон
        r'\b\w+@\w+\.\w+\b',  # Email
    ]
    
    # Паттерн эмодзи
    EMOJI_PATTERN = r'^[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]{3,}'
    
    @abstractmethod
    def parse(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Парсит новости. Должен быть реализован в подклассах.
        
        Args:
            limit: Максимальное количество новостей для парсинга
            
        Returns:
            Список словарей с данными новостей
        """
    
    def is_advertisement(self, title: Optional[str] = None, 
                       summary: Optional[str] = None, 
                       author: Optional[str] = None) -> bool:
        """
        Определяет, является ли новость рекламным материалом.
        
        Args:
            title: Заголовок новости
            summary: Краткое описание
            author: Автор новости
            
        Returns:
            True если новость является рекламой, False иначе
        """
        title = (title or '').lower()
        summary = (summary or '').lower()
        author = (author or '').lower()
        full_text = f"{title} {summary}"
        
        # Проверка по ключевым словам
        for keyword in self.AD_KEYWORDS:
            if keyword in full_text:
                logger.debug(f"Реклама обнаружена по ключевому слову '{keyword}': {title[:50]}")
                return True
        
        # Проверка структурных паттернов
        
        # 1. Слишком много эмодзи в начале заголовка
        if title and re.match(self.EMOJI_PATTERN, title):
            logger.debug(f"Реклама обнаружена по паттерну эмодзи: {title[:50]}")
            return True
        
        # 2. Слишком короткий заголовок
        if len(title) < 10:
            logger.debug(f"Реклама обнаружена по короткому заголовку: {title}")
            return True
        
        # 3. Заголовок в верхнем регистре (проверяем оригинальный title, а не преобразованный)
        if title and title.isupper() and len(title) > 5:
            logger.debug(f"Реклама обнаружена по CAPS заголовку: {title[:50]}")
            return True
        
        # 4. Слишком много восклицательных знаков
        if title.count('!') > 3:
            logger.debug(f"Реклама обнаружена по восклицаниям: {title[:50]}")
            return True
        
        # 5. Проверка на бота в имени автора
        if author and ('bot' in author or author.endswith('_bot')):
            logger.debug(f"Реклама от бота: {author}")
            return True
        
        # 6. Множественные ссылки в тексте
        url_count = summary.count('http://') + summary.count('https://') + summary.count('t.me/')
        if url_count > 2:
            logger.debug(f"Реклама обнаружена по множественным ссылкам ({url_count}): {title[:50]}")
            return True
        
        # 7. Контактная информация
        for pattern in self.CONTACT_PATTERNS:
            if re.search(pattern, full_text):
                logger.debug(f"Реклама обнаружена по контактной информации: {title[:50]}")
                return True
        
        # 8. Повторяющиеся слова (спам-паттерн)
        words = summary.split()
        if len(words) > 10:
            word_counts = {}
            for word in words:
                if len(word) > 3:
                    word_counts[word] = word_counts.get(word, 0) + 1
            max_repeats = max(word_counts.values()) if word_counts else 0
            if max_repeats > 3 and len(words) < 50:
                logger.debug(f"Реклама обнаружена по повторяющимся словам: {title[:50]}")
                return True
        
        return False
    
    def should_skip_item(self, title: Optional[str] = None,
                        summary: Optional[str] = None,
                        author: Optional[str] = None,
                        min_title_length: int = 10,
                        min_summary_length: int = 0) -> bool:
        """
        Проверяет, нужно ли пропустить новость по базовым критериям.
        
        Args:
            title: Заголовок новости
            summary: Краткое описание
            author: Автор новости
            min_title_length: Минимальная длина заголовка
            min_summary_length: Минимальная длина описания
            
        Returns:
            True если новость нужно пропустить, False иначе
        """
        # Проверка на рекламу
        if self.is_advertisement(title, summary, author):
            return True
        
        # Проверка минимальной длины заголовка
        if not title or len(title.strip()) < min_title_length:
            return True
        
        # Проверка минимальной длины описания (если требуется)
        if min_summary_length > 0 and (not summary or len(summary.strip()) < min_summary_length):
            return True
        
        return False
    
    def filter_by_keywords(self, news_item: Dict[str, Any], keywords: List[str]) -> bool:
        """
        Фильтрует новость по ключевым словам.
        
        Если список ключевых слов пуст, пропускает все новости.
        Иначе проверяет наличие хотя бы одного ключевого слова.
        
        Args:
            news_item: Словарь с данными новости
            keywords: Список ключевых слов для фильтрации
            
        Returns:
            True если новость прошла фильтрацию, False иначе
        """
        if not keywords:
            # Если нет ключевых слов, пропускаем все
            return True
        
        # Собираем текст для поиска
        title = (news_item.get('title') or '').lower()
        summary = (news_item.get('summary') or '').lower()
        search_text = f"{title} {summary}"
        
        # Проверяем наличие хотя бы одного ключевого слова
        for keyword in keywords:
            if keyword.lower() in search_text:
                logger.debug(f"Новость прошла фильтрацию по ключевому слову '{keyword}': {title[:50]}")
                return True
        
        logger.debug(f"Новость не прошла фильтрацию по ключевым словам: {title[:50]}")
        return False
