import logging
import httpx
import sys

from openai import OpenAI, RateLimitError, OpenAIError

from ai_bot.config import settings

logger = logging.getLogger(__name__)

proxy_url = settings.PROXY_URL
http_client = httpx.Client(proxy=proxy_url)

client = None
if settings.OPENAI_API_KEY:
    client = OpenAI(
        api_key=settings.OPENAI_API_KEY,
        http_client=http_client
    )


def make_request(instructions: str, prompt: str, temperature: float = 0.7, max_tokens: int = 500) -> str | None:
    """Синхронный запрос к OpenAI API."""
    if not client:
        logger.error("OPENAI_API_KEY is not set")
        return None

    if not settings.OPENAI_MODEL:
        logger.error("OPENAI_MODEL is not set")
        return None

    try:
        # Используем актуальный Chat Completions API
        response = client.chat.completions.create(
            model=settings.OPENAI_MODEL,
            messages=[
                {"role": "system", "content": instructions},
                {"role": "user", "content": prompt}
            ],
            temperature=temperature,
            max_tokens=max_tokens
        )

        result = response.choices[0].message.content
        logger.info(f"OpenAI response received, length: {len(result) if result else 0}")
        return result

    except RateLimitError as e:
        logger.error(f"Rate limit error: {e}")
        return None
    except OpenAIError as e:
        logger.error(f"OpenAI error: {e}")
        return None
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        return None

if __name__ == '__main__':
    import asyncio
    *_, arg_prompt, arg_text = sys.argv
    
    asyncio.run(make_request(arg_prompt, arg_text))