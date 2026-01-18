"""Модуль для публикации постов в Telegram."""

import logging

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
            (settings.TELEGRAM_API_ID or settings.TELERGAM_API_ID) and
            (settings.TELEGRAM_API_HASH or settings.TELERGAM_API_HASH)):

        api_id = settings.TELEGRAM_API_ID or settings.TELERGAM_API_ID
        api_hash = settings.TELEGRAM_API_HASH or settings.TELERGAM_API_HASH
        session_name = settings.TELEGRAM_SESSION_NAME or settings.TELERGAM_SESSION_NAME or 'aibot_session'

        logger.info("Using Telethon client")
        return TelegramClient(session_name, api_id, api_hash), "telethon"

    else:
        logger.error('Neither Bot API token nor Telethon credentials are configured')
        return None, None


def _publish_via_telethon(client: TelegramClient, text: str, channel_name: str) -> bool:
    """Публикация через Telethon"""
    target_channel = channel_name or settings.TELEGRAM_CHANNEL_USERNAME or settings.TELERGAM_CHANNEL_USERNAME
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
            loop.run_until_complete(_publish_telethon_async(client, text, target_channel))
            return True
        finally:
            loop.close()
    except Exception as e:
        logger.error(f'Telethon publishing failed: {e}', exc_info=True)
        return False


async def _publish_telethon_async(client: TelegramClient, text: str, target_channel: str) -> None:
    """Асинхронная публикация через Telethon"""
    await client.connect()

    if not await client.is_user_authorized():
        logger.error('Telegram client not authorized. Use /api/telegram/authorize/ to authorize')
        return

    await client.send_message(target_channel, text)
    logger.info(f'Post published via Telethon to: {target_channel}')


def _publish_via_bot_api(bot_token: str, text: str, channel_name: str) -> bool:
    """Публикация через Bot API"""
    if not HAS_REQUESTS:
        logger.error("requests library not available for Bot API")
        return False

    target_channel = channel_name or settings.TELEGRAM_CHANNEL_USERNAME or settings.TELERGAM_CHANNEL_USERNAME
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


def publish_post(text: str, channel_name: str | None = None) -> bool:
    """
    Публикует пост в Telegram канал.
    Автоматически выбирает между Telethon и Bot API.
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

