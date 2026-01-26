"""Модуль для публикации постов в Telegram."""

import logging
from typing import Optional

from ai_bot.config import settings

logger = logging.getLogger(__name__)
try:
    from telethon import TelegramClient
    HAS_TELETHON = True
except ImportError:
    HAS_TELETHON = False
    logger.warning("Telethon not available, only Bot API will work")

try:
    import requests
    HAS_REQUESTS = True
except ImportError:
    HAS_REQUESTS = False


def _create_telegram_client():
    """Создает клиент для работы с Telegram"""
    # Приоритет: сначала пробуем Bot API (для автоматической публикации)
    if settings.TELEGRAM_BOT_TOKEN:
        logger.info("Using Bot API client")
        return settings.TELEGRAM_BOT_TOKEN, "bot_api"

    # Если нет Bot API токена, пробуем Telethon (для парсинга каналов)
    elif (HAS_TELETHON and
            settings.TELEGRAM_API_ID and
            settings.TELEGRAM_API_HASH):

        api_id = settings.TELEGRAM_API_ID
        api_hash = settings.TELEGRAM_API_HASH
        session_name = settings.TELEGRAM_SESSION_NAME or 'ai_bot_session'
        
        # Используем полный путь к сессии внутри контейнера
        session_path = f'/ai_bot/telegram/telegram_sessions/{session_name}'

        logger.info("Using Telethon client")
        return TelegramClient(session_path, api_id, api_hash), "telethon"

    else:
        logger.error('Neither Bot API token nor Telethon credentials are configured')
        return None, None


def _publish_via_telethon(client: TelegramClient, text: str, channel_name: str) -> bool:
    """Публикация через Telethon"""
    target_channel = channel_name or settings.TELEGRAM_CHANNEL_USERNAME
    if not target_channel:
        logger.error('Telegram channel not configured')
        return False

    if target_channel.startswith('@'):
        target_channel = target_channel[1:]

    try:
        import asyncio
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            result = loop.run_until_complete(_publish_telethon_async(client, text, target_channel))
            # Правильно закрываем клиент перед закрытием loop
            try:
                if client.is_connected():
                    loop.run_until_complete(client.disconnect())
            except Exception:
                pass
            return result
        finally:
            # Закрываем все pending tasks
            pending = asyncio.all_tasks(loop)
            for task in pending:
                task.cancel()
            if pending:
                loop.run_until_complete(asyncio.gather(*pending, return_exceptions=True))
            loop.close()
    except Exception as e:
        logger.error(f'Telethon publishing failed: {e}', exc_info=True)
        return False


async def _publish_telethon_async(client: TelegramClient, text: str, target_channel: str) -> bool:
    """Асинхронная публикация через Telethon"""
    try:
        # Используем start() для автоматической загрузки сессии
        await client.start()

        if not await client.is_user_authorized():
            logger.error('Telegram client not authorized. Use create_session_docker.py to authorize')
            return False

        await client.send_message(target_channel, text)
        logger.info(f'Post published via Telethon to: {target_channel}')
        return True
    except Exception as e:
        logger.error(f'Error publishing via Telethon: {e}', exc_info=True)
        return False


def _publish_via_bot_api(bot_token: str, text: str, channel_name: str) -> bool:
    """Публикация через Bot API"""
    if not HAS_REQUESTS:
        logger.error("requests library not available for Bot API")
        return False

    target_channel = channel_name or settings.TELEGRAM_CHANNEL_USERNAME
    if not target_channel:
        logger.error('Telegram channel not configured')
        return False

    # Bot API требует @ в начале для username каналов
    if not target_channel.startswith('@'):
        target_channel = f'@{target_channel}'

    try:
        url = f"https://api.telegram.org/bot{bot_token}/sendMessage"
        data = {
            'chat_id': target_channel,
            'text': text,
            'parse_mode': 'HTML'
        }

        response = requests.post(url, data=data, timeout=10)
        result = response.json()

        if result.get('ok'):
            logger.info(f'Post published via Bot API to: {target_channel}')
            return True
        else:
            logger.error(f'Bot API error: {result.get("description")}')
            return False

    except Exception as e:
        logger.error(f'Bot API publishing failed: {e}', exc_info=True)
        return False


def publish_post(text: str, channel_name: Optional[str] = None) -> bool:
    """
    Публикует пост в Telegram канал.
    
    Автоматически выбирает между Telethon и Bot API в зависимости от доступных настроек.
    Приоритет: Bot API > Telethon.
    
    Args:
        text: Текст поста для публикации
        channel_name: Username канала (опционально, если не указан - используется из настроек)
        
    Returns:
        True если публикация успешна, False иначе
    """
    client, client_type = _create_telegram_client()

    if not client:
        logger.error('Telegram client not configured. Set either TELEGRAM_API_ID/TELEGRAM_API_HASH or TELEGRAM_BOT_TOKEN')
        return False

    if client_type == "telethon":
        return _publish_via_telethon(client, text, channel_name)
    elif client_type == "bot_api":
        return _publish_via_bot_api(client, text, channel_name)
    else:
        logger.error(f'Unknown client type: {client_type}')
        return False

