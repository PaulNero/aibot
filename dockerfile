FROM python:3.12-slim

WORKDIR /ai_bot

RUN pip install poetry

COPY pyproject.toml poetry.lock ./

RUN poetry install --no-root --no-cache

COPY . .

CMD ["poetry", "run", "uvicorn", "ai_bot.main:app", "--host", "0.0.0.0", "--port", "8006", "--reload"]
