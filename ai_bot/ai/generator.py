import logging

from ai_bot.ai.openai_client import make_request
from ai_bot.db.models import NewsItem, Keyword

logger = logging.getLogger(__name__)

INSTRUCTIONS = """
Вы являетесь профессиональным новостным агентом, специализирующимся на создании привлекательных и информативных новостей.
Сделай краткое, интересное описание новости для Telegram-канала, добавь emoji, call to action
"""


def generate_posts(news: NewsItem) -> str | None:
    """
    Генерирует пост для новости с использованием AI.
    
    Args:
        news: Объект новости для генерации поста
        
    Returns:
        Сгенерированный текст поста или None в случае ошибки
    """
    prompt = f"""
    Source: {news.source if news.source else 'unknown'}
    News: {news.title}
    Summary: {news.summary}
    Link: {news.url}
    Imagine: {news.img}
    Author: {news.author}
    Published at: {news.published_at}

    """

    logger.info(f'Генерация поста для новости: {news.id}')

    # Пытаемся использовать OpenAI
    post_text = make_request(INSTRUCTIONS, prompt)

    if post_text:
        logger.info('Пост сгенерирован через OpenAI')
        return post_text

    # Fallback: простая генерация без AI
    logger.warning('OpenAI недоступен, используем fallback генерацию')
    post_text = generate_fallback_post(news)

    if post_text:
        logger.info('Пост сгенерирован через fallback')
        return post_text

    logger.error(f'Не удалось сгенерировать пост для новости: {news.id}')
    return None


def generate_fallback_post(news: NewsItem) -> str:
    """
    Fallback генерация поста без AI.
    Создает простой но информативный пост из заголовка и краткого описания.
    """
    try:
        # Берем заголовок
        title = news.title if news.title else "Новости"

        # Берем первые 200 символов summary
        summary = news.summary[:200] if news.summary else ""
        if len(news.summary or "") > 200:
            summary += "..."

        # Добавляем emoji и call to action
        emoji = "📰"  # Новости
        if "технолог" in (news.title or "").lower() or "программ" in (news.title or "").lower():
            emoji = "💻"  # Технологии
        elif "игр" in (news.title or "").lower():
            emoji = "🎮"  # Игры
        elif "бизнес" in (news.title or "").lower():
            emoji = "💼"  # Бизнес

        # Формируем пост
        post_parts = [
            f"{emoji} {title}",
            "",
            summary,
            "",
            f"📖 Читать полностью: {news.url}",
            "",
            "#новости #технологии"
        ]

        # Фильтруем пустые строки
        post_parts = [part for part in post_parts if part.strip()]

        return "\n".join(post_parts)

    except Exception as e:
        logger.error(f'Ошибка в fallback генерации: {e}')
        return None