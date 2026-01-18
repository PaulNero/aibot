"""Парсер для Telegram-каналов."""

import logging
import asyncio
from datetime import datetime
from typing import List, Dict, Any, Optional

from telethon import TelegramClient
from telethon.tl.types import Message

from ai_bot.config import settings

logger = logging.getLogger(__name__)


class TelegramParser:
    """Парсер для извлечения сообщений из Telegram-каналов."""
    def __init__(self, channel_username: str):
        self.channel_username = channel_username.lstrip('@')
        self.client = None

    async def _get_client(self) -> Optional[TelegramClient]:
        """Получить или создать Telegram клиент"""
        if not settings.TELERGAM_API_ID or not settings.TELERGAM_API_HASH:
            logger.error('Telegram credentials not set')
            return None

        if not self.client:
            self.client = TelegramClient(
                settings.TELERGAM_SESSION_NAME,
                settings.TELERGAM_API_ID,
                settings.TELERGAM_API_HASH
            )

        if not await self.client.is_connected():
            await self.client.connect()

        if not await self.client.is_user_authorized():
            logger.error('Telegram client not authorized')
            return None

        return self.client

    async def parse(self, limit: int = 50) -> List[Dict[str, Any]]:
        """
        Парсит последние сообщения из Telegram канала

        Args:
            limit: количество сообщений для получения

        Returns:
            Список словарей с данными сообщений
        """
        client = await self._get_client()
        if not client:
            return []

        try:
            # Получаем entity канала
            channel = await client.get_entity(f'@{self.channel_username}')
            logger.info(f'Получаем сообщения из канала: @{self.channel_username}')

            # Получаем последние сообщения
            messages = await client.get_messages(channel, limit=limit)

            news_items = []
            for message in messages:
                if message.message and message.date:  # Проверяем что есть текст и дата
                    news_item = self._message_to_news_item(message)
                    if news_item:
                        news_items.append(news_item)

            logger.info(f'Получено {len(news_items)} сообщений из канала @{self.channel_username}')
            return news_items

        except Exception as e:
            logger.error(f'Ошибка при парсинге канала @{self.channel_username}: {e}', exc_info=True)
            return []
        finally:
            if client:
                await client.disconnect()

    def _message_to_news_item(self, message: Message) -> Optional[Dict[str, Any]]:
        """Преобразует Telegram сообщение в формат новости"""
        try:
            # Пропускаем пустые сообщения или сообщения без текста
            if not message.message or not message.message.strip():
                return None

            # Пропускаем сообщения старше 24 часов (чтобы не дублировать старые новости)
            if (datetime.now() - message.date.replace(tzinfo=None)).days > 1:
                return None

            # Пропускаем forwarded сообщения (часто реклама или репосты)
            if message.forward:
                logger.debug(f"Пропускаем forwarded сообщение: {message.message[:50]}...")
                return None

            # Пропускаем сообщения от ботов (часто рекламные)
            if message.sender and hasattr(message.sender, 'bot') and message.sender.bot:
                logger.debug(f"Пропускаем сообщение от бота: {message.message[:50]}...")
                return None

            # Базовая фильтрация рекламы для Telegram
            # Пропускаем сообщения с множественными эмодзи в начале
            emoji_count = 0
            for char in message.message[:10]:  # Проверяем первые 10 символов
                if ord(char) > 0x1F600 and ord(char) < 0x1F64F:  # Диапазон эмодзи
                    emoji_count += 1
            if emoji_count >= 3:
                logger.debug(f"Пропускаем сообщение с множественными эмодзи: {message.message[:50]}...")
                return None

            # Пропускаем слишком короткие сообщения
            if len(message.message.strip()) < 20:
                logger.debug(f"Пропускаем слишком короткое сообщение: {message.message}")
                return None

            # Создаем summary из первых 500 символов
            summary = message.message[:500]
            if len(message.message) > 500:
                summary += "..."

            return {
                'source': f'tg_{self.channel_username}',
                'title': f'Post from @{self.channel_username}',  # Заголовок для TG постов
                'summary': summary,
                'url': f'https://t.me/{self.channel_username}/{message.id}',
                'author': getattr(message.sender, 'username', 'Unknown') if message.sender else 'Unknown',
                'published_at': message.date.replace(tzinfo=None),
                'raw_text': message.message,  # Полный текст сообщения
                'img': None  # TODO: можно добавить парсинг изображений
            }

        except Exception as e:
            logger.error(f'Ошибка при обработке сообщения: {e}')
            return None


# Асинхронная функция для использования в Celery
async def parse_telegram_channel_async(channel_username: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Асинхронная функция для парсинга Telegram канала"""
    parser = TelegramParser(channel_username)
    return await parser.parse(limit)


def parse_telegram_channel_sync(channel_username: str, limit: int = 50) -> List[Dict[str, Any]]:
    """Синхронная функция для парсинга Telegram канала (для использования в Celery)"""
    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)
    try:
        return loop.run_until_complete(parse_telegram_channel_async(channel_username, limit))
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