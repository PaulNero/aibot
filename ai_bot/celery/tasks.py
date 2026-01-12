from ai_bot.celery.celery_worker import celery_app

@celery_app.task()
def parse_news():
    print('Parsing news...')
