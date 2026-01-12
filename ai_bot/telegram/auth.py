import asyncio
import logging

from telethon import TelegramClient
from telethon.errors import SessionPasswordNeededError

from ai_bot.config import settings

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


async def interactive_authorize():
    if not settings.TELERGAM_API_ID or not settings.TELERGAM_API_HASH:
        logger.error('Telegram credentials not configured. Set TELERGAM_API_ID and TELERGAM_API_HASH in .env')
        return
    
    client = TelegramClient(
        settings.TELERGAM_SESSION_NAME,
        settings.TELERGAM_API_ID,
        settings.TELERGAM_API_HASH
    )
    
    try:
        await client.connect()
        
        if await client.is_user_authorized():
            me = await client.get_me()
            logger.info(f'Уже авторизован как {me.first_name} {me.last_name or ""} (@{me.username or "без username"})')
            return
        
        phone = input('Введите номер телефона (в формате +7XXXXXXXXXX): ').strip()
        if not phone:
            logger.error('Номер телефона не может быть пустым')
            return
        
        await client.send_code_request(phone)
        logger.info('Код подтверждения отправлен в Telegram')
        
        code = input('Введите код из Telegram: ').strip()
        if not code:
            logger.error('Код не может быть пустым')
            return
        
        try:
            await client.sign_in(phone, code)
            me = await client.get_me()
            logger.info(f'Успешно авторизован как {me.first_name} {me.last_name or ""} (@{me.username or "без username"})')
        except SessionPasswordNeededError:
            password = input('Введите пароль двухфакторной аутентификации: ').strip()
            if not password:
                logger.error('Пароль не может быть пустым')
                return
            
            await client.sign_in(password=password)
            me = await client.get_me()
            logger.info(f'Успешно авторизован как {me.first_name} {me.last_name or ""} (@{me.username or "без username"})')
    
    except Exception as e:
        logger.error(f'Ошибка при авторизации: {e}', exc_info=True)
    finally:
        await client.disconnect()


if __name__ == '__main__':
    asyncio.run(interactive_authorize())
