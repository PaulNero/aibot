import asyncio
import os
from telethon import TelegramClient

# Читаем из переменных окружения или .env файла
def load_env():
    """Загружаем переменные из .env файла"""
    env_file = '.env'
    if os.path.exists(env_file):
        with open(env_file, 'r') as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith('#') and '=' in line:
                    key, value = line.split('=', 1)
                    os.environ[key.strip()] = value.strip()

load_env()

API_ID = int(os.getenv('TELEGRAM_API_ID', '0'))
API_HASH = os.getenv('TELEGRAM_API_HASH', '')
SESSION_NAME = os.getenv('TELEGRAM_SESSION_NAME', 'ai_bot_session')
PHONE_NUMBER = os.getenv('PHONE_NUMBER', '')

async def main():
    print("🚀 Создание сессии Telethon...")
    print(f"📱 Телефон: {PHONE_NUMBER}")
    print(f"🔑 API ID: {API_ID}")
    print(f"📁 Сессия: {SESSION_NAME}")
    print()

    if not API_ID or not API_HASH or not PHONE_NUMBER:
        print("❌ Ошибка: не все переменные установлены!")
        print("Проверьте .env файл:")
        print("- TELEGRAM_API_ID")
        print("- TELEGRAM_API_HASH")
        print("- PHONE_NUMBER")
        return

    client = TelegramClient(SESSION_NAME, API_ID, API_HASH)

    try:
        print("📡 Подключение к Telegram...")
        await client.start(phone=PHONE_NUMBER)
        print("✅ Сессия создана и авторизована!")
        print(f"📂 Файл сессии: {SESSION_NAME}.session")
    except Exception as e:
        print(f"❌ Ошибка: {e}")
    finally:
        await client.disconnect()

    print("\n💡 Теперь скопируйте сессию в контейнер:")
    print(f"docker cp {SESSION_NAME}.session jr_final-celery-worker-1:/ai_bot/telegram/telegram_sessions/")

if __name__ == "__main__":
    asyncio.run(main())