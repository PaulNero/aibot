import logging
import httpx
import sys

from openai import OpenAI, RateLimitError, OpenAIError

from ai_bot.config import settings

logger = logging.getLogger(__name__)

proxy_url = settings.PROXY_URL
http_client = httpx.Client(proxy=proxy_url)

# client: OpenAI | None = OpenAI(api_key=settings.OPENAI_API_KEY, 
#                                 http_client = "http://18.199.183.77:49232")

client = None
if settings.OPENAI_API_KEY:
    client = OpenAI(
        api_key=settings.OPENAI_API_KEY,
        http_client=http_client
    )


async def make_request(instructions: str, prompt: str, temperature: float = 0.7, max_tokens: int = 500) -> str | None:
    if not client:
        raise ValueError("OPENAI_API_KEY is not set")
    if not settings.OPENAI_MODEL:
        raise ValueError("OPENAI_MODEL is not set")
    try:
        response = client.responses.create(
            model=settings.OPENAI_MODEL,
            instructions=instructions,
            input=prompt,
            temperature=temperature,
            max_output_tokens=max_tokens
        )

    except RateLimitError as e:
        logger.error(f"Rate limit error: {e}")
        return None
    except OpenAIError as e:
        logger.error(f"OpenAI error: {e}")
        return None
    except Exception as e:
        logger.error(f"Error: {e}")
        return None

    print(response.output_text)
    return response.output_text

if __name__ == '__main__':
    import asyncio
    *_, arg_prompt, arg_text = sys.argv
    
    asyncio.run(make_request(arg_prompt, arg_text))