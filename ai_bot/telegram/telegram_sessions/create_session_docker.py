import asyncio
import os
from telethon import TelegramClient

API_ID = int(os.getenv('TELEGRAM_API_ID', '0'))
API_HASH = os.getenv('TELEGRAM_API_HASH', '')
SESSION_NAME = 'ai_bot_session'
PHONE_NUMBER = os.getenv('PHONE_NUMBER', '')

async def main():
    print("🚀 Создание сессии Telethon в Docker...")
    print(f"📱 Телефон: {PHONE_NUMBER}")

    if not API_ID or not API_HASH or not PHONE_NUMBER:
        print("❌ Ошибка: переменные не установлены")
        return

    client = TelegramClient(f'/ai_bot/telegram/telegram_sessions/{SESSION_NAME}', API_ID, API_HASH)

    try:
        print("📡 Подключение...")
        await client.start(phone=PHONE_NUMBER)
        print("✅ Сессия создана!")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await client.disconnect()

if __name__ == "__main__":
    asyncio.run(main())