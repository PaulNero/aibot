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
    """Проверяет наличие дубликатов новостей по URL или заголовку."""
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
    """Сохраняет список новостей в базу данных."""
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
    """Парсит новости из веб-источника."""
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
    """Парсит новости из Telegram-канала."""
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

        # Парсим канал
        news_items = parse_telegram_channel_sync(channel_username, limit=20)

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
    """Определяет, является ли новость рекламным материалом."""
    title = (news_item.title or '').lower()
    summary = (news_item.summary or '').lower()
    author = (news_item.author or '').lower()
    full_text = f"{title} {summary}"

    # === Ключевые слова рекламы ===
    ad_keywords = [
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

    # Проверяем ключевые слова в заголовке и тексте
    for keyword in ad_keywords:
        if keyword in full_text:
            logger.info(f"Реклама обнаружена по ключевому слову '{keyword}': {news_item.title}")
            return True

    # === Структурные паттерны ===

    # 1. Слишком много эмодзи в начале (признак рекламы)
    emoji_pattern = r'^[\U0001F600-\U0001F64F\U0001F300-\U0001F5FF\U0001F680-\U0001F6FF\U0001F1E0-\U0001F1FF]{3,}'
    import re
    if re.match(emoji_pattern, news_item.title or ''):
        logger.info(f"Реклама обнаружена по паттерну эмодзи: {news_item.title}")
        return True

    # 2. Слишком короткий заголовок (менее 10 символов, часто реклама)
    if len(news_item.title or '') < 10:
        logger.info(f"Реклама обнаружена по короткому заголовку: {news_item.title}")
        return True

    # 3. Заголовок состоит только из заглавных букв (часто в рекламе)
    if news_item.title and news_item.title.isupper() and len(news_item.title) > 5:
        logger.info(f"Реклама обнаружена по CAPS заголовку: {news_item.title}")
        return True

    # 4. Слишком много восклицательных знаков
    if (news_item.title or '').count('!') > 3:
        logger.info(f"Реклама обнаружена по восклицаниям: {news_item.title}")
        return True

    # 5. Для Telegram: проверка на бота в имени автора
    if 'bot' in author or author.endswith('_bot'):
        logger.info(f"Реклама от бота: {news_item.author}")
        return True

    # 6. Проверка на множественные ссылки в тексте (признак рекламы)
    url_count = summary.count('http://') + summary.count('https://') + summary.count('t.me/')
    if url_count > 2:
        logger.info(f"Реклама обнаружена по множественным ссылкам ({url_count}): {news_item.title}")
        return True

    # 7. Проверка на контактную информацию (часто в рекламе)
    contact_patterns = [
        r'@\w+',  # Telegram username
        r'\+?\d{10,}',  # Телефон
        r'\b\w+@\w+\.\w+\b',  # Email
    ]
    for pattern in contact_patterns:
        if re.search(pattern, full_text):
            logger.info(f"Реклама обнаружена по контактной информации: {news_item.title}")
            return True

    # 8. Проверка на повторяющиеся слова (спам-паттерн)
    words = summary.split()
    if len(words) > 10:
        word_counts = {}
        for word in words:
            if len(word) > 3:  # Только слова длиннее 3 символов
                word_counts[word] = word_counts.get(word, 0) + 1
        # Если какое-то слово повторяется более 3 раз в коротком тексте
        max_repeats = max(word_counts.values()) if word_counts else 0
        if max_repeats > 3 and len(words) < 50:
            logger.info(f"Реклама обнаружена по повторяющимся словам: {news_item.title}")
            return True

    return False


def filter_news_by_keywords(session: Session, news_item: NewsItem) -> bool:
    """Фильтрует новость по ключевым словам."""
    from ai_bot.db.models import Keyword

    # Сначала проверяем на рекламу - если это реклама, сразу отфильтровываем
    if is_advertisement(news_item):
        logger.info(f"Новость '{news_item.title}' отфильтрована как реклама")
        return False

    # Получаем все активные ключевые слова
    keywords = session.query(Keyword).all()

    if not keywords:
        logger.warning("Нет ключевых слов для фильтрации - пропускаем все новости")
        return True  # Если нет ключевых слов, пропускаем все

    # Собираем текст для поиска: title + summary
    search_text = f"{news_item.title or ''} {news_item.summary or ''}".lower()

    # Проверяем наличие каждого ключевого слова
    for keyword in keywords:
        if keyword.word.lower() in search_text:
            logger.info(f"Новость '{news_item.title}' прошла фильтрацию по ключевому слову '{keyword.word}'")
            return True

    logger.info(f"Новость '{news_item.title}' не прошла фильтрацию по ключевым словам")
    return False
