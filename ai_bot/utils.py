"""Утилиты для работы с новостями и парсерами."""

import logging
from datetime import datetime
from typing import List, Dict, Any

from sqlalchemy.orm import Session

from ai_bot.db.models import Source, NewsItem, Post
from ai_bot.db.models_utils import SourceType
from ai_bot.news_parser.sites import HabrParser, SiteParser

logger = logging.getLogger(__name__)


def check_duplicate(session: Session, url: str = None, title: str = None) -> bool:
    """
    Проверяет наличие дубликатов новостей по URL или заголовку.
    
    Args:
        session: Сессия базы данных
        url: URL новости для проверки
        title: Заголовок новости для проверки
        
    Returns:
        True если дубликат найден, False иначе
    """
    if url:
        existing = session.query(NewsItem).filter(NewsItem.url == url).first()
        if existing:
            return True
    
    if title:
        existing = session.query(NewsItem).filter(NewsItem.title == title).first()
        if existing:
            return True
    
    return False


def save_news_items(session: Session, news_items: List[Dict[str, Any]]) -> int:
    """
    Сохраняет список новостей в базу данных.
    
    Args:
        session: Сессия базы данных
        news_items: Список словарей с данными новостей
        
    Returns:
        Количество успешно сохраненных новостей
    """
    saved_count = 0
    
    for item_data in news_items:
        if check_duplicate(session, url=item_data.get('url'), title=item_data.get('title')):
            logger.debug(f"Пропущен дубликат: {item_data.get('title', 'Без названия')}")
            continue

        try:
            news_item = NewsItem(
                source=item_data.get('source', 'unknown'),
                title=item_data['title'],
                summary=item_data.get('summary', ''),
                url=item_data.get('url'),
                img=item_data.get('img'),
                author=item_data.get('author'),
                published_at=item_data.get('published_at', datetime.now()),
                raw_text=item_data.get('raw_text'),
            )
            # Сначала добавляем news_item, чтобы получить id
            session.add(news_item)
            session.flush()  # Получаем id для news_item
            
            # Теперь создаем Post с правильным news_id
            new_post = Post(news_id=news_item.id)
            session.add(new_post)
            saved_count += 1
            logger.debug(f"Добавлена новость: {item_data.get('title', 'Без названия')}")
        except Exception as e:
            logger.error(f"Ошибка при сохранении новости '{item_data.get('title', 'Без названия')}': {e}")
            continue

    try:
        session.commit()
        logger.info(f"Сохранено новостей: {saved_count} из {len(news_items)}")
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка при коммите транзакции: {e}")
        raise
    
    return saved_count


def parse_site_source(session: Session, source: Source) -> int:
    """
    Парсит новости из веб-источника.
    
    Args:
        session: Сессия базы данных
        source: Объект источника для парсинга
        
    Returns:
        Количество сохраненных новостей
    """
    if source.type != SourceType.SITE or not source.enabled:
        return 0
    
    # Сохраняем имя источника до обработки
    source_name = source.name
    source_url = source.url
    
    try:
        parser: SiteParser
        if 'habr' in source_name.lower() or 'habr' in (source_url or '').lower():
            parser = HabrParser()
        elif 'tproger' in source_name.lower() or 'tproger' in (source_url or '').lower():
            from ai_bot.news_parser.sites import TProgerParser
            parser = TProgerParser()
        else:
            logger.warning(f"Парсер для источника '{source_name}' не найден")
            return 0
        
        logger.info(f"Парсинг новостей с источника: {source_name}")
        news_items = parser.parse()
        
        if not news_items:
            logger.warning(f"Не найдено новостей с источника: {source_name}")
            return 0
        
        # Фильтруем новости без title
        valid_news_items = [item for item in news_items if item.get('title')]
        if len(valid_news_items) < len(news_items):
            logger.warning(f"Отфильтровано {len(news_items) - len(valid_news_items)} новостей без заголовка")
        
        if not valid_news_items:
            logger.warning(f"Все новости с источника '{source_name}' не имеют заголовка")
            return 0
        
        saved = save_news_items(session, valid_news_items)
        logger.info(f"Источник '{source_name}': сохранено {saved} новостей")
        return saved
        
    except Exception as e:
        logger.error(f"Ошибка при парсинге источника '{source_name}': {e}", exc_info=True)
        session.rollback()
        return 0


def parse_telegram_source(session: Session, source: Source) -> int:
    """
    Парсит новости из Telegram-канала.
    
    Args:
        session: Сессия базы данных
        source: Объект источника Telegram-канала
        
    Returns:
        Количество сохраненных новостей
    """
    if source.type != SourceType.TG or not source.enabled:
        return 0

    # Импортируем здесь чтобы избежать циклических импортов
    from ai_bot.news_parser.telegram import parse_telegram_channel_sync

    source_name = source.name
    channel_username = source.url  # URL для TG источников - это username канала

    if not channel_username:
        logger.warning(f"Не указан username канала для источника: {source_name}")
        return 0

    try:
        logger.info(f"Парсинг Telegram-канала: {channel_username}")

        # Парсим канал (используем синхронную версию, которая создает свой event loop)
        try:
            news_items = parse_telegram_channel_sync(channel_username, limit=10)
        except RuntimeError as e:
            if "event loop" in str(e).lower():
                logger.warning(f"Не удалось запустить парсинг Telegram (проблема с event loop): {e}")
                logger.info("Попробуйте запустить парсинг через Celery задачу")
                return 0
            raise

        if not news_items:
            logger.warning(f"Не найдено новостей в канале: {channel_username}")
            return 0

        # Сохраняем новости
        saved = save_news_items(session, news_items)
        logger.info(f"Источник '{source_name}' ({channel_username}): сохранено {saved} новостей")
        return saved

    except Exception as e:
        logger.error(f"Ошибка при парсинге Telegram-канала '{source_name}': {e}", exc_info=True)
        session.rollback()
        return 0


def is_advertisement(news_item: NewsItem) -> bool:
    """
    Определяет, является ли новость рекламным материалом.
    
    Использует логику из BaseParser для единообразной фильтрации.
    
    Args:
        news_item: Объект новости для проверки
        
    Returns:
        True если новость является рекламой, False иначе
    """
    from ai_bot.news_parser.base import BaseParser
    
    # Создаем временный экземпляр парсера для использования методов фильтрации
    parser = BaseParser.__new__(BaseParser)  # Создаем без вызова __init__
    
    return parser.is_advertisement(
        title=news_item.title,
        summary=news_item.summary,
        author=news_item.author
    )


def filter_news_by_keywords(session: Session, news_item: NewsItem) -> bool:
    """
    Фильтрует новость по ключевым словам.
    
    Если ключевых слов нет в БД, пропускает все новости.
    Если есть - проверяет наличие хотя бы одного ключевого слова.
    
    Args:
        session: Сессия базы данных
        news_item: Объект новости для фильтрации
        
    Returns:
        True если новость прошла фильтрацию, False иначе
    """
    from ai_bot.db.models import Keyword
    from ai_bot.news_parser.base import BaseParser

    # Сначала проверяем на рекламу - если это реклама, сразу отфильтровываем
    if is_advertisement(news_item):
        logger.info(f"Новость '{news_item.title}' отфильтрована как реклама")
        return False

    # Получаем все активные ключевые слова
    keywords = session.query(Keyword).all()

    if not keywords:
        logger.warning("Нет ключевых слов для фильтрации - пропускаем все новости")
        return True  # Если нет ключевых слов, пропускаем все

    # Создаем временный экземпляр парсера для использования методов фильтрации
    parser = BaseParser.__new__(BaseParser)
    
    # Преобразуем новость в словарь для использования метода фильтрации
    news_dict = {
        'title': news_item.title,
        'summary': news_item.summary,
        'author': news_item.author
    }
    
    # Получаем список ключевых слов
    keyword_words = [kw.word for kw in keywords]
    
    # Используем метод фильтрации из BaseParser
    result = parser.filter_by_keywords(news_dict, keyword_words)
    
    if result:
        logger.info(f"Новость '{news_item.title}' прошла фильтрацию по ключевым словам")
    else:
        logger.info(f"Новость '{news_item.title}' не прошла фильтрацию по ключевым словам")
    
    return result
