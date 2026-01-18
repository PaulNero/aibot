import logging

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from ai_bot.config import settings

logger = logging.getLogger(__name__)

_telegram_client: TelegramClient | None = None


def get_telegram_client() -> TelegramClient | None:
    global _telegram_client

    if not settings.TELERGAM_API_ID or not settings.TELERGAM_API_HASH:
        logger.error('Telegram credentials not set')
        return None

    if not _telegram_client:
        _telegram_client = TelegramClient(
            settings.TELERGAM_SESSION_NAME,
            settings.TELERGAM_API_ID,
            settings.TELERGAM_API_HASH
        )
    return _telegram_client


async def authorize_telegram(phone: str, code: str | None = None, password: str | None = None) -> dict:
    if not settings.TELERGAM_API_ID or not settings.TELERGAM_API_HASH:
        return {
            'success': False,
            'message': 'Telegram credentials not configured'
        }
    
    client = TelegramClient(
        settings.TELERGAM_SESSION_NAME,
        settings.TELERGAM_API_ID,
        settings.TELERGAM_API_HASH
    )
    
    try:
        await client.connect()
        
        if await client.is_user_authorized():
            me = await client.get_me()
            return {
                'success': True,
                'message': f'Уже авторизован как {me.first_name} {me.last_name or ""}',
                'phone': me.phone,
                'username': me.username
            }
        
        if not code:
            await client.send_code_request(phone)
            return {
                'success': True,
                'message': 'Код подтверждения отправлен в Telegram',
                'next_step': 'code'
            }
        
        try:
            await client.sign_in(phone, code)
            me = await client.get_me()
            return {
                'success': True,
                'message': f'Успешно авторизован как {me.first_name} {me.last_name or ""}',
                'phone': me.phone,
                'username': me.username
            }
        except SessionPasswordNeededError:
            if not password:
                return {
                    'success': False,
                    'message': 'Требуется пароль двухфакторной аутентификации',
                    'next_step': 'password'
                }
            
            await client.sign_in(password=password)
            me = await client.get_me()
            return {
                'success': True,
                'message': f'Успешно авторизован как {me.first_name} {me.last_name or ""}',
                'phone': me.phone,
                'username': me.username
            }
    
    except Exception as e:
        logger.error(f'Ошибка при авторизации Telegram: {e}', exc_info=True)
        return {
            'success': False,
            'message': f'Ошибка авторизации: {str(e)}'
        }
    finally:
        await client.disconnect()

