import asyncio
import logging
from datetime import datetime

from ai_bot.ai.generator import generate_posts
from ai_bot.db.models import NewsItem
from ai_bot.db.models_utils import PostStatus
from ai_bot.db.db_manager import get_db_sync
from ai_bot.db.models import Source, Post
from ai_bot.db.models_utils import SourceType
from ai_bot.telegram.publisher import publish_post
from ai_bot.utils import parse_site_source, parse_telegram_source, filter_news_by_keywords
from ai_bot.celery.celery_worker import celery_app

logger = logging.getLogger(__name__)


@celery_app.task(name='ai_bot.celery.tasks.parse_news', bind=True, max_retries=3)
def parse_news(self):
    """
    Задача Celery для парсинга новостей из всех активных источников.
    
    Получает активные источники из БД, парсит их (сайты и Telegram-каналы)
    и сохраняет новости. Автоматически запускает генерацию постов после успешного парсинга.
    
    Returns:
        Словарь с результатами: {'status': 'success', 'saved': int, 'sources_processed': int}
    """
    logger.info('Начало парсинга новостей...')

    try:
        db_gen = get_db_sync()
        session = next(db_gen)

        try:
            sources = session.query(Source).filter(Source.enabled == True).all()

            if not sources:
                logger.warning("Не найдено активных источников для парсинга")
                return {'status': 'success', 'saved': 0, 'sources_processed': 0}

            logger.info(f"Найдено активных источников: {len(sources)}")

            total_saved = 0
            for source in sources:
                # Сохраняем имя источника до обработки, чтобы избежать проблем с rollback
                source_name = source.name
                try:
                    source_type = source.type

                    if source_type == SourceType.SITE:
                        saved = parse_site_source(session, source)
                    elif source_type == SourceType.TG:
                        saved = parse_telegram_source(session, source)
                    else:
                        logger.warning(f"Неизвестный тип источника: {source_type} для '{source_name}'")
                        saved = 0

                    total_saved += saved

                except Exception as e:
                    logger.error(f"Ошибка при обработке источника '{source_name}': {e}", exc_info=True)
                    session.rollback()
                    continue

            logger.info(f'Парсинг завершен. Всего сохранено новостей: {total_saved}')

            result = {
                'status': 'success',
                'saved': total_saved,
                'sources_processed': len(sources)
            }

            # Автоматически запускаем генерацию постов после успешного парсинга
            if total_saved > 0:
                logger.info(f'Запускаем генерацию постов для {total_saved} новых новостей')
                generate_posts_task.delay()

            return result
        except Exception as e:
            logger.error(f'Ошибка при парсинге новостей: {e}', exc_info=True)
            session.rollback()
            raise
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass

    except Exception as e:
        logger.error(f'Критическая ошибка при парсинге новостей: {e}', exc_info=True)
        raise self.retry(exc=e, countdown=60)


@celery_app.task(name='ai_bot.celery.tasks.generate_posts', bind=True, max_retries=3)
def generate_posts_task(self):
    """
    Задача Celery для генерации постов из новостей.
    
    Обрабатывает посты со статусом NEW: фильтрует по ключевым словам,
    генерирует текст через AI и обновляет статус на GENERATED.
    Автоматически запускает публикацию после успешной генерации.
    
    Returns:
        Словарь с результатами: {'status': 'success', 'generated': int}
    """
    logger.info('Выполняем задачу генерации постов по новости')
    try:
        db_gen = get_db_sync()
        session = next(db_gen)

        try:
            # Находим посты со статусом NEW и получаем связанные новости
            posts = session.query(Post).filter(Post.status == PostStatus.NEW).all()
            if not posts:
                logger.info('Нет новых постов для генерации')
                return {'status': 'success', 'generated': 0}

            generated_count = 0
            for post in posts:
                try:
                    news_item = session.query(NewsItem).filter(NewsItem.id == post.news_id).first()
                    if not news_item:
                        logger.warning(f'Новость с id {post.news_id} не найдена')
                        continue

                    # Фильтруем новость по ключевым словам
                    if not filter_news_by_keywords(session, news_item):
                        logger.info(f'Новость {news_item.id} не прошла фильтрацию по ключевым словам, пропускаем генерацию')
                        post.status = PostStatus.FAILED
                        continue

                    post_text = generate_posts(news_item)
                    if not post_text:
                        post.status = PostStatus.FAILED
                        logger.warning(f'Не удалось сгенерировать пост для новости {news_item.id}')
                        continue

                    # Обновляем существующий пост
                    post.generated_text = post_text
                    post.status = PostStatus.GENERATED
                    generated_count += 1
                    logger.info(f'Сгенерирован пост для новости {news_item.id}')

                    # Коммитим каждую успешную генерацию
                    session.commit()

                except Exception as e:
                    logger.error(f'Ошибка при генерации поста для новости {post.news_id}: {e}', exc_info=True)
                    post.status = PostStatus.FAILED
                    # Коммитим даже при ошибке, чтобы статус FAILED сохранился
                    session.commit()
                    continue

            # Финальный коммит для remaining постов
            session.commit()
            logger.info(f'Генерация завершена. Сгенерировано постов: {generated_count}')

            if generated_count > 0:
                logger.info(f'Запускаем публикацию постов для {generated_count} новых новостей')
                publish_posts_task.delay()

            return {'status': 'success', 'generated': generated_count}

        except Exception as e:
            logger.error(f'Ошибка при генерации постов: {e}', exc_info=True)
            session.rollback()
            raise
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass

    except Exception as e:
        logger.error(f'Критическая ошибка при генерации постов: {e}', exc_info=True)
        raise self.retry(exc=e, countdown=60)


@celery_app.task(name='ai_bot.celery.tasks.publish_posts', bind=True, max_retries=3)
def publish_posts_task(self):
    """
    Задача Celery для публикации постов в Telegram канал.
    
    Обрабатывает посты со статусом GENERATED: публикует их в Telegram
    через Bot API или Telethon и обновляет статус на PUBLISHED или FAILED.
    
    Returns:
        Словарь с результатами: {'status': 'success', 'published': int, 'failed': int}
    """
    logger.info('Начинаем публикацию постов')
    try:
        db_gen = get_db_sync()
        session = next(db_gen)
        try:
            posts = session.query(Post).filter(Post.status == PostStatus.GENERATED).all()
            if not posts:
                logger.info('Нет новых постов для публикации')
                return {'status': 'success', 'published': 0, 'failed': 0}

            published = failed = 0
            for post in posts:
                if not post.generated_text:
                    logger.warning(f'Пост {post.id} не имеет сгенерированного текста')
                    continue
                
                try:
                    success = publish_post(post.generated_text)

                    if success:
                        post.status = PostStatus.PUBLISHED
                        post.published_at = datetime.now()
                        logger.info(f'Опубликован пост {post.id}')
                        published += 1
                    else:
                        post.status = PostStatus.FAILED
                        logger.warning(f'Не удалось опубликовать пост {post.id}')
                        failed += 1

                except Exception as e:
                    logger.error(f'Ошибка при публикации поста {post.id}: {e}', exc_info=True)
                    post.status = PostStatus.FAILED
                    failed += 1
                    continue

            session.commit()
            logger.info(f'Публикация завершена. Опубликовано постов: {published}. Провалено постов: {failed}')
            return {'status': 'success', 'published': published, 'failed': failed}
        except Exception as e:
            logger.error(f'Ошибка при публикации постов: {e}', exc_info=True)
            session.rollback()
            raise
        finally:
            try:
                next(db_gen)
            except StopIteration:
                pass

    except Exception as e:
        logger.error(f'Критическая ошибка при публикации постов: {e}', exc_info=True)
        raise self.retry(exc=e, countdown=60)