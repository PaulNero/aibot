import logging
from datetime import datetime
from typing import List, Dict, Any

from sqlalchemy.orm import Session

from ai_bot.db.models import Source, NewsItem, Post
from ai_bot.db.models_utils import SourceType
from ai_bot.news_parser.sites import HabrParser, SiteParser

logger = logging.getLogger(__name__)


def check_duplicate(session: Session, url: str = None, title: str = None) -> bool:
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
                img=item_data.deg('img'),
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
    if source.type != SourceType.SITE or not source.enabled:
        return 0
    
    # Сохраняем имя источника до обработки
    source_name = source.name
    source_url = source.url
    
    try:
        parser: SiteParser
        if 'habr' in source_name.lower() or 'habr' in (source_url or '').lower():
            parser = HabrParser()
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
    if source.type != SourceType.TG or not source.enabled:
        return 0
    
    # TODO: Реализовать парсинг Telegram-каналов
    logger.warning(f"Парсинг Telegram-каналов еще не реализован для источника: {source.name}")
    return 0
