"""Парсер для Telegram-каналов через Telethon."""

import logging
import asyncio
from datetime import datetime, timedelta
from typing import List, Dict, Any, Optional

from ai_bot.config import settings
from ai_bot.news_parser.base import BaseParser

logger = logging.getLogger(__name__)

try:
    from telethon import TelegramClient
    from telethon.tl.functions.channels import JoinChannelRequest
    from telethon.errors import ChannelPrivateError, UsernameNotOccupiedError, FloodWaitError
    HAS_TELETHON = True
except ImportError:
    HAS_TELETHON = False
    logger.error("Telethon не установлен. Установите: poetry add telethon")


class TelegramParser(BaseParser):
    """Парсер для извлечения сообщений из Telegram-каналов через Telethon."""

    def __init__(self, channel_username: str):
        """
        Инициализация парсера Telegram-канала.
        
        Args:
            channel_username: Username канала (с @ или без)
        """
        super().__init__()
        self.channel_username = channel_username.lstrip('@')

    def _get_client(self) -> Optional[TelegramClient]:
        """
        Создает и возвращает Telethon клиент.
        
        Returns:
            TelegramClient или None если настройки не сконфигурированы
        """
        if not HAS_TELETHON:
            logger.error('Telethon не установлен')
            return None

        if not settings.TELEGRAM_API_ID or not settings.TELEGRAM_API_HASH:
            logger.error('TELEGRAM_API_ID и TELEGRAM_API_HASH не настроены')
            return None

        # Используем путь к сессии внутри контейнера
        session_path = f'/ai_bot/telegram/telegram_sessions/{settings.TELEGRAM_SESSION_NAME}'
        
        client = TelegramClient(
            session_path,
            settings.TELEGRAM_API_ID,
            settings.TELEGRAM_API_HASH
        )
        return client

    async def _ensure_subscribed(self, client: TelegramClient) -> bool:
        """
        Убеждается, что клиент подписан на канал.
        
        Пытается получить сообщения, если не получается - пытается подписаться.
        
        Args:
            client: Telethon клиент
            
        Returns:
            True если доступ к каналу есть, False иначе
        """
        try:
            # Пытаемся получить информацию о канале
            entity = await client.get_entity(self.channel_username)
            
            # Пробуем получить сообщения - если не подписан, будет ошибка
            try:
                # Пробуем получить одно сообщение для проверки доступа
                await client.get_messages(entity, limit=1)
                return True
            except (ChannelPrivateError, ValueError, Exception) as e:
                # Если не подписан или нет доступа, пытаемся подписаться
                logger.info(f'Попытка подписаться на канал @{self.channel_username}')
                try:
                    await client(JoinChannelRequest(entity))
                    logger.info(f'Успешно подписались на канал @{self.channel_username}')
                    return True
                except Exception as join_error:
                    logger.warning(f'Не удалось подписаться на канал @{self.channel_username}: {join_error}')
                    # Продолжаем попытку парсинга - возможно, канал публичный и доступен без подписки
                    return True
        except UsernameNotOccupiedError:
            logger.error(f'Канал @{self.channel_username} не найден')
            return False
        except Exception as e:
            logger.warning(f'Ошибка при проверке подписки на @{self.channel_username}: {e}, продолжаем...')
            # Продолжаем попытку парсинга
            return True

    def parse(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Синхронный метод для парсинга Telegram-канала.
        
        Обертка над parse_async для совместимости с BaseParser.
        
        Args:
            limit: Максимальное количество сообщений для парсинга
            
        Returns:
            Список словарей с данными новостей
        """
        return asyncio.run(self.parse_async(limit=limit))

    async def parse_async(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Асинхронно парсит последние сообщения из Telegram канала через Telethon

        Args:
            limit: количество сообщений для получения

        Returns:
            Список словарей с данными сообщений
        """
        if not HAS_TELETHON:
            logger.error('Telethon не установлен для парсинга Telegram')
            return []

        client = self._get_client()
        if not client:
            return []

        try:
            # Используем start() вместо connect() для автоматической загрузки сессии
            await client.start()
            
            if not client.is_connected():
                logger.error('Не удалось подключиться к Telegram')
                return []

            if not await client.is_user_authorized():
                logger.error('Telethon клиент не авторизован. Создайте сессию через create_session_docker.py')
                return []

            # Убеждаемся, что подписаны на канал
            if not await self._ensure_subscribed(client):
                return []

            # Получаем сообщения из канала
            logger.info(f'Запрашиваем сообщения из канала @{self.channel_username}')
            
            try:
                messages = await client.get_messages(self.channel_username, limit=min(limit, 100))
            except FloodWaitError as e:
                logger.warning(f'FloodWait: нужно подождать {e.seconds} секунд')
                return []
            except Exception as e:
                logger.error(f'Ошибка при получении сообщений: {e}')
                return []

            logger.info(f'Получено {len(messages)} сообщений из канала @{self.channel_username}')

            news_items = []
            for message in messages:
                news_item = self._message_to_news_item(message)
                if news_item:
                    news_items.append(news_item)

            logger.info(f'После фильтрации осталось {len(news_items)} новостей из @{self.channel_username}')
            return news_items

        except Exception as e:
            logger.error(f'Ошибка при парсинге Telegram-канала @{self.channel_username}: {e}', exc_info=True)
            return []
        finally:
            try:
                await client.disconnect()
            except Exception:
                pass

    def _message_to_news_item(self, message) -> Optional[Dict[str, Any]]:
        """
        Преобразует Telethon сообщение в формат новости.
        
        Фильтрует старые сообщения, forwarded, сообщения от ботов и рекламу.
        
        Args:
            message: Объект сообщения Telethon
            
        Returns:
            Словарь с данными новости или None если сообщение отфильтровано
        """
        try:
            # Пропускаем сообщения без текста
            if not message.message or not message.message.strip():
                return None

            message_text = message.message.strip()

            # Пропускаем сообщения старше 24 часов (чтобы не дублировать старые новости)
            message_date = message.date
            if message_date.tzinfo:
                message_date = message_date.replace(tzinfo=None)
            
            if (datetime.now() - message_date) > timedelta(days=1):
                logger.debug(f"Пропускаем старое сообщение: {message_text[:50]}...")
                return None

            # Пропускаем forwarded сообщения (часто реклама или репосты)
            if message.forward:
                logger.debug(f"Пропускаем forwarded сообщение: {message_text[:50]}...")
                return None

            # Пропускаем сообщения от ботов (часто рекламные)
            if message.sender and hasattr(message.sender, 'bot') and message.sender.bot:
                logger.debug(f"Пропускаем сообщение от бота: {message_text[:50]}...")
                return None

            # Получаем автора для фильтрации
            author = None
            if message.sender:
                if hasattr(message.sender, 'username') and message.sender.username:
                    author = message.sender.username
                elif hasattr(message.sender, 'first_name'):
                    author = message.sender.first_name

            # Используем базовую фильтрацию из BaseParser
            # Для Telegram используем message_text как title и summary
            if self.should_skip_item(title=message_text, summary=message_text, author=author, min_title_length=20):
                return None

            # Создаем title из первых слов сообщения (до 100 символов)
            title = message_text[:100]
            if len(message_text) > 100:
                # Обрезаем по последнему пробелу
                last_space = title.rfind(' ')
                if last_space > 50:
                    title = title[:last_space] + '...'
                else:
                    title = title + '...'

            # Создаем summary из первых 500 символов
            summary = message_text[:500]
            if len(message_text) > 500:
                summary += "..."

            # Получаем автора
            author = 'Unknown'
            if message.sender:
                if hasattr(message.sender, 'username') and message.sender.username:
                    author = message.sender.username
                elif hasattr(message.sender, 'first_name'):
                    author = message.sender.first_name or 'Unknown'

            # Получаем ID сообщения для URL
            message_id = message.id if hasattr(message, 'id') else None
            url = f'https://t.me/{self.channel_username}/{message_id}' if message_id else None

            return {
                'source': f'tg_{self.channel_username}',
                'title': title,
                'summary': summary,
                'url': url,
                'author': author,
                'published_at': message_date,
                'raw_text': message_text,  # Полный текст сообщения
                'img': None  # Изображения пока не парсятся
            }

        except Exception as e:
            logger.error(f'Ошибка при обработке сообщения: {e}', exc_info=True)
            return None


def parse_telegram_channel_sync(channel_username: str, limit: int = 50) -> List[Dict[str, Any]]:
    """
    Синхронная функция для парсинга Telegram канала (для использования в Celery)
    
    Args:
        channel_username: username канала (без @)
        limit: количество сообщений для получения
        
    Returns:
        Список словарей с данными новостей
    """
    parser = TelegramParser(channel_username)
    
    # Проверяем, есть ли уже запущенный event loop
    try:
        loop = asyncio.get_event_loop()
        if loop.is_running():
            # Если loop уже запущен, создаем новый в отдельном потоке
            import concurrent.futures
            with concurrent.futures.ThreadPoolExecutor() as executor:
                future = executor.submit(_run_in_new_loop, parser, limit)
                return future.result()
        else:
            # Loop существует, но не запущен - используем его
            return loop.run_until_complete(parser.parse_async(limit))
    except RuntimeError:
        # Нет event loop - создаем новый
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            return loop.run_until_complete(parser.parse_async(limit))
        finally:
            loop.close()


def _run_in_new_loop(parser: TelegramParser, limit: int) -> List[Dict[str, Any]]:
    """Запускает парсинг в новом event loop в отдельном потоке."""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(parser.parse_async(limit))
    finally:
        loop.close()


if __name__ == '__main__':
    # Тестовый запуск
    import sys
    if len(sys.argv) > 1:
        channel = sys.argv[1]
        print(f'Парсинг канала: {channel}')
        result = parse_telegram_channel_sync(channel, limit=5)
        print(f'Получено {len(result)} сообщений:')
        for item in result:
            print(f"- {item['title']}: {item['summary'][:100]}...")
    else:
        print("Использование: python telegram.py @channel_username")
