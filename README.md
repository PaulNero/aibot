# PROJECT M4: AI-генератор постов для Telegram


poetry run uvicorn ai_bot.main:app


redis-server
poetry run python -m celery -A ai_bot.celery.celery_worker worker --loglevel=info
poetry run python -m celery -A ai_bot.celery.celery_worker beat --loglevel=info