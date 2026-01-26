"""
Админ бот для управления системой AI бота на базе Aiogram 3.x.
Позволяет просматривать и изменять источники и ключевые слова.
"""

import logging
from typing import List

from aiogram import Bot, Dispatcher, Router, F
from aiogram.client.default import DefaultBotProperties
from aiogram.enums import ParseMode
from aiogram.filters import Command, CommandStart
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.types import (
    Message,
    CallbackQuery,
    InlineKeyboardMarkup,
    InlineKeyboardButton,
)

from ai_bot.config import settings
from ai_bot.db.db_manager import get_db_sync
from ai_bot.db.models import Source, Keyword
from ai_bot.db.models_utils import SourceType

logger = logging.getLogger(__name__)

# Определяем состояния для FSM
class AddSourceStates(StatesGroup):
    waiting_for_name = State()
    waiting_for_url = State()

class AddKeywordStates(StatesGroup):
    waiting_for_word = State()


class AdminBot:
    """Админ бот для управления системой на базе Aiogram."""

    def __init__(self):
        self.bot: Bot = None
        self.dp: Dispatcher = None
        self.router: Router = Router()
        self.allowed_user_ids = self._parse_admin_user_ids()

    def _parse_admin_user_ids(self) -> List[int]:
        """Парсит список ID админов из настроек."""
        if not settings.TELEGRAM_ADMIN_USER_IDS:
            logger.warning("TELEGRAM_ADMIN_USER_IDS not set. Admin bot will not work.")
            return []

        try:
            return [int(uid.strip()) for uid in settings.TELEGRAM_ADMIN_USER_IDS.split(',')]
        except ValueError as e:
            logger.error(f"Invalid TELEGRAM_ADMIN_USER_IDS format: {e}")
            return []

    def _is_admin(self, user_id: int) -> bool:
        """Проверяет, является ли пользователь админом."""
        return user_id in self.allowed_user_ids

    def _create_main_keyboard(self) -> InlineKeyboardMarkup:
        """Создает главную клавиатуру."""
        keyboard = [
            [InlineKeyboardButton(text="📊 Статистика", callback_data="stats")],
            [InlineKeyboardButton(text="📋 Источники", callback_data="sources_list")],
            [InlineKeyboardButton(text="🔑 Ключевые слова", callback_data="keywords_list")],
            [InlineKeyboardButton(text="➕ Добавить источник", callback_data="source_add")],
            [InlineKeyboardButton(text="➕ Добавить ключевое слово", callback_data="keyword_add")],
        ]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    def _create_back_keyboard(self, callback_data: str = "back_to_main") -> InlineKeyboardMarkup:
        """Создает клавиатуру с кнопкой назад."""
        keyboard = [[InlineKeyboardButton(text="⬅️ Назад", callback_data=callback_data)]]
        return InlineKeyboardMarkup(inline_keyboard=keyboard)

    async def start_command(self, message: Message):
        """Обработчик команды /start."""
        if not self._is_admin(message.from_user.id):
            await message.reply("❌ У вас нет доступа к админ панели.")
            return

        await message.reply(
            "🤖 *Админ панель AI бота*\n\n"
            "Выберите действие:",
            reply_markup=self._create_main_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

    async def stats_callback(self, callback: CallbackQuery):
        """Показывает статистику системы."""
        if not self._is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        await callback.answer()

        # Получаем статистику из базы данных
        session = get_db_sync()
        try:
            total_sources = session.query(Source).count()
            active_sources = session.query(Source).filter(Source.enabled == True).count()
            total_keywords = session.query(Keyword).count()

            # Получаем количество новостей и постов через прямой запрос
            from sqlalchemy import text
            news_count = session.execute(text("SELECT COUNT(*) FROM news_items")).scalar()
            posts_total = session.execute(text("SELECT COUNT(*) FROM posts")).scalar()
            posts_published = session.execute(text("SELECT COUNT(*) FROM posts WHERE status = 'PUBLISHED'")).scalar()

            stats_text = (
                "📊 *Статистика системы*\n\n"
                f"📋 Источники: {total_sources} (активных: {active_sources})\n"
                f"🔑 Ключевые слова: {total_keywords}\n"
                f"📰 Новости: {news_count}\n"
                f"📝 Посты: {posts_total} (опубликовано: {posts_published})"
            )

        except Exception as e:
            logger.error(f"Error getting stats: {e}")
            stats_text = "❌ Ошибка при получении статистики"
        finally:
            session.close()

        await callback.message.edit_text(
            stats_text,
            reply_markup=self._create_back_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

    def setup_handlers(self):
        """Настраивает все обработчики."""
        # Команды
        self.router.message.register(self.start_command, CommandStart())

        # Callback запросы
        self.router.callback_query.register(self.stats_callback, F.data == "stats")
        # Другие обработчики будут добавлены позже

    async def run(self):
        """Запускает бота."""
        if not settings.TELEGRAM_ADMIN_BOT_TOKEN:
            logger.error("TELEGRAM_ADMIN_BOT_TOKEN not set. Admin bot will not start.")
            return

        # Создаем бота и диспетчер
        self.bot = Bot(
            token=settings.TELEGRAM_ADMIN_BOT_TOKEN,
            default=DefaultBotProperties(parse_mode=ParseMode.HTML)
        )
        self.dp = Dispatcher()
        self.dp.include_router(self.router)

        # Настраиваем обработчики
        self.setup_handlers()

        logger.info("Admin bot started")
        try:
            await self.dp.start_polling(self.bot)
        finally:
            await self.bot.session.close()


def run_admin_bot():
    """Функция для запуска админ бота."""
    import asyncio

    bot = AdminBot()
    asyncio.run(bot.run())


if __name__ == "__main__":
    run_admin_bot()

    async def sources_list_callback(self, callback: CallbackQuery):
        """Показывает список источников."""
        if not self._is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        await callback.answer()

        session = get_db_sync()
        try:
            sources = session.query(Source).order_by(Source.name).all()

            if not sources:
                text = "📋 *Источники*\n\nИсточников нет."
                keyboard = [
                    [InlineKeyboardButton(text="➕ Добавить", callback_data="source_add")],
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
                ]
            else:
                text = "📋 *Источники*\n\n"
                keyboard = []
                for source in sources:
                    status = "✅" if source.enabled else "❌"
                    source_type = "🌐 Сайт" if source.type == SourceType.SITE else "📱 Telegram"

                    # Создаем кнопки для управления каждым источником
                    action = "source_disable" if source.enabled else "source_enable"
                    action_text = "🚫" if source.enabled else "✅"

                    keyboard.append([
                        InlineKeyboardButton(
                            text=f"{status} {source_type} {source.name}",
                            callback_data=f"source_info_{source.id}"
                        )
                    ])
                    keyboard.append([
                        InlineKeyboardButton(text=f"{action_text} Вкл/Выкл", callback_data=f"{action}_{source.id}"),
                        InlineKeyboardButton(text="🗑️ Удалить", callback_data=f"source_delete_{source.id}")
                    ])
                    text += "\n"

                # Добавляем кнопки управления
                keyboard.append([InlineKeyboardButton(text="➕ Добавить", callback_data="source_add")])
                keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")])

            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

        except Exception as e:
            logger.error(f"Error getting sources: {e}")
            text = "❌ Ошибка при получении источников"
            reply_markup = self._create_back_keyboard("back_to_main")
        finally:
            session.close()

        await callback.message.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def keywords_list_callback(self, callback: CallbackQuery):
        """Показывает список ключевых слов."""
        if not self._is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        await callback.answer()

        session = get_db_sync()
        try:
            keywords = session.query(Keyword).order_by(Keyword.word).all()

            if not keywords:
                text = "🔑 *Ключевые слова*\n\nКлючевых слов нет."
                keyboard = [
                    [InlineKeyboardButton(text="➕ Добавить", callback_data="keyword_add")],
                    [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")]
                ]
            else:
                text = "🔑 *Ключевые слова*\n\n"
                keyboard = []
                for i, keyword in enumerate(keywords):
                    # Создаем кнопки для удаления (максимум 5 в строке для читаемости)
                    if i % 5 == 0:
                        keyboard.append([])
                    keyboard[-1].append(
                        InlineKeyboardButton(text=f"❌ {keyword.word}", callback_data=f"keyword_delete_{keyword.id}")
                    )

                # Добавляем кнопки управления
                keyboard.append([InlineKeyboardButton(text="➕ Добавить", callback_data="keyword_add")])
                keyboard.append([InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_main")])

                text += f"Всего: {len(keywords)} слов\n\nНажмите ❌ для удаления слова"

            reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

        except Exception as e:
            logger.error(f"Error getting keywords: {e}")
            text = "❌ Ошибка при получении ключевых слов"
            reply_markup = self._create_back_keyboard("back_to_main")
        finally:
            session.close()

        await callback.message.edit_text(
            text,
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def back_to_main_callback(self, callback: CallbackQuery):
        """Возвращает в главное меню."""
        if not self._is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        await callback.answer()

        await callback.message.edit_text(
            "🤖 *Админ панель AI бота*\n\n"
            "Выберите действие:",
            reply_markup=self._create_main_keyboard(),
            parse_mode=ParseMode.MARKDOWN
        )

    async def source_add_callback(self, callback: CallbackQuery, state: FSMContext):
        """Начинает процесс добавления источника."""
        if not self._is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        await callback.answer()

        keyboard = [
            [InlineKeyboardButton(text="🌐 Сайт", callback_data="source_add_type_site")],
            [InlineKeyboardButton(text="📱 Telegram канал", callback_data="source_add_type_tg")],
            [InlineKeyboardButton(text="⬅️ Отмена", callback_data="back_to_main")]
        ]
        reply_markup = InlineKeyboardMarkup(inline_keyboard=keyboard)

        await callback.message.edit_text(
            "➕ *Добавление источника*\n\n"
            "Выберите тип источника:",
            reply_markup=reply_markup,
            parse_mode=ParseMode.MARKDOWN
        )

    async def source_add_type_callback(self, callback: CallbackQuery, state: FSMContext):
        """Обработка выбора типа источника."""
        if not self._is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        await callback.answer()

        callback_data = callback.data

        if callback_data == "source_add_type_site":
            source_type = "site"
            type_text = "🌐 сайта"
        elif callback_data == "source_add_type_tg":
            source_type = "tg"
            type_text = "📱 Telegram канала"
        else:
            return

        # Сохраняем тип в состоянии FSM
        await state.update_data(source_type=source_type)
        await state.set_state(AddSourceStates.waiting_for_name)

        await callback.message.edit_text(
            f"➕ *Добавление источника: {type_text}*\n\n"
            f"Отправьте название источника:",
            parse_mode=ParseMode.MARKDOWN
        )

    async def source_name_message(self, message: Message, state: FSMContext):
        """Обработка ввода названия источника."""
        if not self._is_admin(message.from_user.id):
            return

        source_name = message.text
        data = await state.get_data()
        source_type = data.get('source_type')

        # Сохраняем название и переходим к следующему шагу
        await state.update_data(source_name=source_name)
        await state.set_state(AddSourceStates.waiting_for_url)

        type_text = "🌐 сайта" if source_type == "site" else "📱 Telegram канала"

        await message.reply(
            f"➕ *Добавление источника: {type_text}*\n\n"
            f"Название: `{source_name}`\n\n"
            f"Теперь отправьте URL источника:",
            parse_mode=ParseMode.MARKDOWN
        )

    async def source_url_message(self, message: Message, state: FSMContext):
        """Обработка ввода URL источника."""
        if not self._is_admin(message.from_user.id):
            return

        source_url = message.text
        data = await state.get_data()
        source_name = data.get('source_name')
        source_type = data.get('source_type')

        # Сохраняем в базу данных
        session = get_db_sync()
        try:
            # Проверяем, существует ли уже источник
            existing = session.query(Source).filter(
                Source.name.ilike(source_name) | Source.url.ilike(source_url)
            ).first()

            if existing:
                await message.reply(
                    f"❌ Источник уже существует:\n"
                    f"Название: {existing.name}\n"
                    f"URL: {existing.url}"
                )
            else:
                # Создаем новый источник
                from datetime import datetime
                new_source = Source(
                    name=source_name,
                    url=source_url,
                    type=SourceType.SITE if source_type == "site" else SourceType.TG,
                    enabled=True,
                    created_at=datetime.now()
                )
                session.add(new_source)
                session.commit()

                await message.reply(
                    f"✅ Источник успешно добавлен!\n\n"
                    f"Название: {source_name}\n"
                    f"URL: {source_url}\n"
                    f"Тип: {'🌐 Сайт' if source_type == 'site' else '📱 Telegram канал'}",
                    reply_markup=self._create_main_keyboard()
                )

        except Exception as e:
            logger.error(f"Error adding source: {e}")
            await message.reply("❌ Ошибка при добавлении источника")
        finally:
            session.close()

        # Очищаем состояние
        await state.clear()

    async def keyword_add_callback(self, callback: CallbackQuery, state: FSMContext):
        """Начинает процесс добавления ключевого слова."""
        if not self._is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        await callback.answer()

        # Устанавливаем состояние
        await state.set_state(AddKeywordStates.waiting_for_word)

        await callback.message.edit_text(
            "➕ *Добавление ключевого слова*\n\n"
            "Отправьте ключевое слово:",
            parse_mode=ParseMode.MARKDOWN
        )

    async def keyword_word_message(self, message: Message, state: FSMContext):
        """Обработка ввода ключевого слова."""
        if not self._is_admin(message.from_user.id):
            return

        word = message.text

        # Сохраняем в базу данных
        session = get_db_sync()
        try:
            # Проверяем, существует ли уже ключевое слово
            existing = session.query(Keyword).filter(Keyword.word.ilike(word)).first()

            if existing:
                await message.reply(
                    f"❌ Ключевое слово `{word}` уже существует",
                    reply_markup=self._create_main_keyboard()
                )
            else:
                # Создаем новое ключевое слово
                from datetime import datetime
                new_keyword = Keyword(
                    word=word.lower(),
                    created_at=datetime.now()
                )
                session.add(new_keyword)
                session.commit()

                await message.reply(
                    f"✅ Ключевое слово `{word}` успешно добавлено!",
                    reply_markup=self._create_main_keyboard()
                )

        except Exception as e:
            logger.error(f"Error adding keyword: {e}")
            await message.reply("❌ Ошибка при добавлении ключевого слова")
        finally:
            session.close()

        # Очищаем состояние
        await state.clear()

    async def source_toggle_callback(self, callback: CallbackQuery):
        """Включает/выключает источник."""
        if not self._is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        await callback.answer()

        callback_data = callback.data
        parts = callback_data.split('_', 2)
        if len(parts) < 3:
            return

        action = parts[1]  # enable или disable
        source_id = parts[2]
        enable = action == "enable"

        session = get_db_sync()
        try:
            source = session.query(Source).filter(Source.id == source_id).first()

            if not source:
                await callback.message.edit_text(
                    "❌ Источник не найден",
                    reply_markup=self._create_back_keyboard("sources_list")
                )
                return

            # Меняем статус
            source.enabled = enable
            session.commit()

            action_text = "включен" if enable else "выключен"
            await callback.message.edit_text(
                f"✅ Источник `{source.name}` {action_text}!",
                reply_markup=self._create_back_keyboard("sources_list")
            )

        except Exception as e:
            logger.error(f"Error toggling source: {e}")
            await callback.message.edit_text(
                "❌ Ошибка при изменении статуса источника",
                reply_markup=self._create_back_keyboard("sources_list")
            )
        finally:
            session.close()

    async def source_delete_callback(self, callback: CallbackQuery):
        """Удаляет источник."""
        if not self._is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        await callback.answer()

        callback_data = callback.data
        parts = callback_data.split('_', 2)
        if len(parts) < 3:
            return

        source_id = parts[2]

        session = get_db_sync()
        try:
            source = session.query(Source).filter(Source.id == source_id).first()

            if not source:
                await callback.message.edit_text(
                    "❌ Источник не найден",
                    reply_markup=self._create_back_keyboard("sources_list")
                )
                return

            # Удаляем источник
            name = source.name
            session.delete(source)
            session.commit()

            await callback.message.edit_text(
                f"✅ Источник `{name}` удален!",
                reply_markup=self._create_back_keyboard("sources_list")
            )

        except Exception as e:
            logger.error(f"Error deleting source: {e}")
            await callback.message.edit_text(
                "❌ Ошибка при удалении источника",
                reply_markup=self._create_back_keyboard("sources_list")
            )
        finally:
            session.close()

    async def keyword_delete_callback(self, callback: CallbackQuery):
        """Удаляет ключевое слово."""
        if not self._is_admin(callback.from_user.id):
            await callback.answer("❌ Доступ запрещен")
            return

        await callback.answer()

        callback_data = callback.data
        parts = callback_data.split('_', 2)
        if len(parts) < 3:
            return

        keyword_id = parts[2]

        session = get_db_sync()
        try:
            keyword = session.query(Keyword).filter(Keyword.id == keyword_id).first()

            if not keyword:
                await callback.message.edit_text(
                    "❌ Ключевое слово не найдено",
                    reply_markup=self._create_back_keyboard("keywords_list")
                )
                return

            # Удаляем ключевое слово
            word = keyword.word
            session.delete(keyword)
            session.commit()

            await callback.message.edit_text(
                f"✅ Ключевое слово `{word}` удалено!",
                reply_markup=self._create_back_keyboard("keywords_list")
            )

        except Exception as e:
            logger.error(f"Error deleting keyword: {e}")
            await callback.message.edit_text(
                "❌ Ошибка при удалении ключевого слова",
                reply_markup=self._create_back_keyboard("keywords_list")
            )
        finally:
            session.close()

    def setup_handlers(self):
        """Настраивает все обработчики."""
        # Команды
        self.router.message.register(self.start_command, CommandStart())

        # Callback запросы
        self.router.callback_query.register(self.stats_callback, F.data == "stats")
        self.router.callback_query.register(self.sources_list_callback, F.data == "sources_list")
        self.router.callback_query.register(self.keywords_list_callback, F.data == "keywords_list")
        self.router.callback_query.register(self.source_add_callback, F.data == "source_add")
        self.router.callback_query.register(self.keyword_add_callback, F.data == "keyword_add")
        self.router.callback_query.register(self.back_to_main_callback, F.data == "back_to_main")

        # Типы источников
        self.router.callback_query.register(self.source_add_type_callback, F.data.startswith("source_add_type_"))

        # Управление источниками
        self.router.callback_query.register(self.source_toggle_callback, F.data.startswith(("source_enable_", "source_disable_")))
        self.router.callback_query.register(self.source_delete_callback, F.data.startswith("source_delete_"))

        # Управление ключевыми словами
        self.router.callback_query.register(self.keyword_delete_callback, F.data.startswith("keyword_delete_"))

        # FSM состояния
        self.router.message.register(self.source_name_message, AddSourceStates.waiting_for_name)
        self.router.message.register(self.source_url_message, AddSourceStates.waiting_for_url)
        self.router.message.register(self.keyword_word_message, AddKeywordStates.waiting_for_word)
