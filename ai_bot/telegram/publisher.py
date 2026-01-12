import logging

from telethon import TelegramClient

from ai_bot.config import settings

logger = logging.getLogger(__name__)


def _create_telegram_client() -> TelegramClient | None:
    if not settings.TELERGAM_API_ID or not settings.TELERGAM_API_HASH:
        logger.error('Telegram credentials not set')
        return None
    
    return TelegramClient(
        settings.TELERGAM_SESSION_NAME,
        settings.TELERGAM_API_ID,
        settings.TELERGAM_API_HASH
    )


async def publish_post(text: str, channel_name: str | None = None) -> bool:
    client = _create_telegram_client()
    if not client:
        logger.error('Telegram client not set')
        return False

    target_channel = channel_name or settings.TELERGAM_CHANNEL_USERNAME
    if not target_channel:
        logger.error('Telegram channel not configured')
        return False
    
    if target_channel.startswith('@'):
        target_channel = target_channel[1:]

    try:
        await client.connect()
        
        if not await client.is_user_authorized():
            logger.error('Telegram client not authorized. Use /api/telegram/authorize/ to authorize')
            return False

        await client.send_message(target_channel, text)
        logger.info(f'Пост успешно опубликован в канал: {target_channel}')
        return True
    except Exception as e:
        logger.error(f'Publishing post failed: {e}', exc_info=True)
        return False
    finally:
        await client.disconnect()

