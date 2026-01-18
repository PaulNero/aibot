#!/usr/bin/env python3
"""
Тестовый скрипт для проверки цепочки обработки новостей:
парсинг → фильтрация → генерация → публикация
"""

import asyncio
import logging
from datetime import datetime

from ai_bot.db.db_manager import init_db, get_db_sync
from ai_bot.db.models import Keyword, NewsItem, Post
from ai_bot.db.models_utils import PostStatus
from ai_bot.news_parser.sites import HabrParser
from ai_bot.news_parser.telegram import parse_telegram_channel_sync
from ai_bot.utils import save_news_items, filter_news_by_keywords, is_advertisement
from ai_bot.ai.generator import generate_posts

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


async def test_pipeline():
    """Тестирование полной цепочки обработки"""

    logger.info("🚀 Начинаем тестирование цепочки обработки новостей")

    # Инициализируем БД
    await init_db()

    db_gen = get_db_sync()
    session = next(db_gen)

    try:
        # === ШАГ 1: Парсинг новостей ===
        logger.info("📄 ШАГ 1: Парсинг новостей")

        # Парсим Habr
        habr_parser = HabrParser()
        habr_news = habr_parser.parse()
        logger.info(f"📄 Спарсено {len(habr_news)} новостей с Habr")

        # Сохраняем новости
        saved_habr = save_news_items(session, habr_news[:2])  # Возьмем только 2 для теста
        logger.info(f"💾 Сохранено {saved_habr} новостей из Habr")

        # Парсим Telegram (если настроен)
        try:
            tg_news = parse_telegram_channel_sync('telegram', limit=2)
            if tg_news:
                saved_tg = save_news_items(session, tg_news)
                logger.info(f"💾 Сохранено {saved_tg} новостей из Telegram")
            else:
                logger.warning("⚠️  Не удалось спарсить Telegram новости (возможно не настроены credentials)")
        except Exception as e:
            logger.warning(f"⚠️  Ошибка при парсинге Telegram: {e}")

        # === ШАГ 2: Добавляем ключевые слова для фильтрации ===
        logger.info("🔍 ШАГ 2: Настройка фильтрации")

        # Добавляем тестовые ключевые слова
        keywords_to_add = ['Python', 'AI', 'машинное обучение', 'программирование', 'JavaScript', 'веб-разработка']
        for word in keywords_to_add:
            existing = session.query(Keyword).filter(Keyword.word.ilike(word)).first()
            if not existing:
                keyword = Keyword(word=word, created_at=datetime.now())
                session.add(keyword)
                logger.info(f"➕ Добавлено ключевое слово: {word}")

        session.commit()

        # Создаем тестовую "рекламную" новость для проверки фильтрации
        logger.info("🎭 Создаем тестовую рекламную новость для проверки фильтрации")
        ad_news = NewsItem(
            source='test',
            title='КУПИТЬ ТЕЛЕФОНЫ ПО СКИДКЕ! АКЦИЯ!!!',
            summary='Супер скидки на все модели! Звоните +79999999999 или пишите в ЛС @shop_bot',
            author='ShopBot',
            published_at=datetime.now(),
            raw_text='Рекламный текст с контактной информацией'
        )
        session.add(ad_news)
        session.flush()

        # Создаем Post для рекламной новости
        ad_post = Post(news_id=ad_news.id)
        session.add(ad_post)
        session.commit()

        logger.info(f"🎭 Создана тестовая рекламная новость ID: {ad_news.id}")

        # === ШАГ 3: Фильтрация и генерация ===
        logger.info("🤖 ШАГ 3: Фильтрация и генерация постов")

        # Получаем все новости
        news_items = session.query(NewsItem).all()
        logger.info(f"📋 Найдено {len(news_items)} новостей в БД")

        # Показываем статистику по типам новостей
        ad_count = 0
        normal_count = 0
        for news in news_items:
            if is_advertisement(news):
                ad_count += 1
            else:
                normal_count += 1

        logger.info(f"📊 Классификация новостей: {normal_count} нормальных, {ad_count} рекламных")

        generated_count = 0
        filtered_by_keywords = 0
        filtered_by_ads = 0

        for news in news_items:
            # Создаем Post для новости (если не существует)
            existing_post = session.query(Post).filter(Post.news_id == news.id).first()
            if existing_post:
                continue

            post = Post(news_id=news.id)
            session.add(post)
            session.flush()  # Получаем ID

            # Сначала проверяем на рекламу
            if is_advertisement(news):
                logger.info(f"🚫 Новость '{news.title[:50]}...' отфильтрована как реклама")
                post.status = PostStatus.FAILED
                filtered_by_ads += 1
                continue

            # Фильтруем по ключевым словам
            if not filter_news_by_keywords(session, news):
                logger.info(f"❌ Новость '{news.title[:50]}...' не прошла фильтрацию по ключевым словам")
                post.status = PostStatus.FAILED
                filtered_by_keywords += 1
                continue

            # Генерируем пост
            try:
                post_text = generate_posts(news)
                if post_text:
                    post.generated_text = post_text
                    post.status = PostStatus.GENERATED
                    generated_count += 1
                    logger.info(f"✅ Сгенерирован пост для новости: {news.title[:50]}...")
                else:
                    post.status = PostStatus.FAILED
                    logger.warning(f"❌ Не удалось сгенерировать пост для новости: {news.id}")
            except Exception as e:
                logger.error(f"❌ Ошибка генерации поста для новости {news.id}: {e}")
                post.status = PostStatus.FAILED

        session.commit()
        logger.info(f"🤖 Сгенерировано {generated_count} постов")

        # === ШАГ 4: Публикация ===
        logger.info("📢 ШАГ 4: Публикация постов")

        # Получаем сгенерированные посты
        posts_to_publish = session.query(Post).filter(Post.status == PostStatus.GENERATED).all()
        logger.info(f"📋 Найдено {len(posts_to_publish)} постов для публикации")

        published_count = 0
        for post in posts_to_publish:
            if post.generated_text:
                try:
                    # Публикуем (тестовый режим - без реальной отправки)
                    logger.info(f"📢 Публикация поста {post.id}...")
                    logger.info(f"📝 Текст поста: {post.generated_text[:100]}...")

                    # Для тестирования закомментируем реальную публикацию
                    # success = await publish_post(post.generated_text)
                    success = True  # Имитируем успешную публикацию

                    if success:
                        post.status = PostStatus.PUBLISHED
                        post.published_at = datetime.now()
                        published_count += 1
                        logger.info(f"✅ Пост {post.id} успешно опубликован")
                    else:
                        post.status = PostStatus.FAILED
                        logger.error(f"❌ Не удалось опубликовать пост {post.id}")

                except Exception as e:
                    logger.error(f"❌ Ошибка при публикации поста {post.id}: {e}")
                    post.status = PostStatus.FAILED

        session.commit()
        logger.info(f"📢 Опубликовано {published_count} постов")

        # === ИТОГИ ===
        logger.info("🎉 ТЕСТИРОВАНИЕ ЗАВЕРШЕНО!")
        logger.info(f"📊 Результаты:")
        logger.info(f"   • Спарсено новостей: {len(news_items)}")
        logger.info(f"   • Отфильтровано рекламы: {filtered_by_ads}")
        logger.info(f"   • Отфильтровано по ключам: {filtered_by_keywords}")
        logger.info(f"   • Сгенерировано постов: {generated_count}")
        logger.info(f"   • Опубликовано постов: {published_count}")

    except Exception as e:
        logger.error(f"💥 Критическая ошибка при тестировании: {e}", exc_info=True)
        session.rollback()
    finally:
        try:
            next(db_gen)
        except StopIteration:
            pass


if __name__ == '__main__':
    asyncio.run(test_pipeline())