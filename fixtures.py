"""
Фикстуры для заполнения базы данных начальными данными
"""
import logging
from datetime import datetime

from ai_bot.db.db_manager import sync_session_factory
from ai_bot.db.models import Source
from ai_bot.db.models_utils import SourceType

logger = logging.getLogger(__name__)


def create_fixtures_sync():
    session = sync_session_factory()
    try:
        sources_to_create = [
            {
                'name': 'Habr',
                'type': SourceType.SITE,
                'url': 'https://habr.com/',
                'enabled': True
            },
            {
                'name': 'tproger',
                'type': SourceType.SITE,
                'url': 'https://tproger.ru/',
                'enabled': False
            },
            {
                'name': 'Reddit',
                'type': SourceType.SITE,
                'url': 'https://www.reddit.com/',
                'enabled': False
            },
            {
                'name': 'Telegram News',
                'type': SourceType.TG,
                'url': 'telegram',
                'enabled': False
            },
            {
                'name': 'Durov Channel',
                'type': SourceType.TG,
                'url': 'durov',
                'enabled': False
            }
        ]
        
        created_count = 0
        skipped_count = 0
        for source_data in sources_to_create:
            existing = session.query(Source).filter(Source.name.ilike(f"%{source_data['name']}%")).first()
            if existing:
                logger.info(f"Источник '{source_data['name']}' уже существует: {existing.name} (id: {existing.id}, enabled: {existing.enabled})")
                skipped_count += 1
                continue
            
            source = Source(
                type=source_data['type'],
                name=source_data['name'],
                url=source_data['url'],
                enabled=source_data['enabled'],
                created_at=datetime.now()
            )
            session.add(source)
            created_count += 1
            logger.info(f"Создан источник: {source.name} (id: {source.id}, enabled: {source.enabled})")
        
        session.commit()
        logger.info(f"Создано источников: {created_count}, пропущено: {skipped_count}, всего: {len(sources_to_create)}")
    except Exception as e:
        session.rollback()
        logger.error(f"Ошибка при создании фикстур: {e}", exc_info=True)
        raise
    finally:
        session.close()




if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
    logger.info("Создание фикстур для базы данных...")
    create_fixtures_sync()
    logger.info("Готово!")