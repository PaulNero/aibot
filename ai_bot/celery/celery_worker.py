"""Конфигурация Celery для асинхронной обработки задач."""

import platform
from datetime import timedelta
from celery import Celery
from ai_bot.config import settings

celery_app = Celery(
    'ai_bot',
    broker=settings.CELERY_BROKER_URL,
    backend=settings.CELERY_RESULT_BACKEND,
    include=['ai_bot.celery.tasks']
)

celery_app.conf.update(
    task_serializer = 'json',
    accept_content = ['json'],
    result_serializer = 'json',
    
    queue='ai_bot',
    task_routes={
        'tasks.parse_news':{
            'queue':'ai_bot',
        },
    },
    
    task_acks_late=True,
    task_time_limit=600,  # 10 минут
    task_soft_time_limit=300,  # 5 минут
    
    worker_prefetch_multiplier=1,
    # Исправление для работы на Windows
    worker_cool='solo' if platform.system() == 'Windows' else 'prefork',
    worker_concurrency=1 if platform.system() == 'Windows' else None,
    
    default_queue='default',
    default_exchange='default',
    default_routing_key='default',
    default_retry_delay=10,
    
    timezone='Europe/Moscow',
    enable_utc=True,
    beat_schedule={
        'parse_news': {
            'task': 'ai_bot.celery.tasks.parse_news',
            'schedule': timedelta(minutes=settings.PARSE_INTERVAL_MINUTES),
        }
    }
)

if __name__ == '__main__':
    celery_app.start()