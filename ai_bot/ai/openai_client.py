import logging
import httpx
import sys
import requests

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


def make_request_ollama(instructions: str, prompt: str, temperature: float = 0.7, max_tokens: int = 500) -> str | None:
    """
    Запрос к локальной Ollama LLM.
    """
    try:
        url = f"{settings.OLLAMA_BASE_URL}/api/generate"

        full_prompt = f"{instructions}\n\n{prompt}"

        data = {
            "model": settings.OLLAMA_MODEL,
            "prompt": full_prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }

        logger.info(f'Запрос к Ollama: {settings.OLLAMA_MODEL}')
        response = requests.post(url, json=data, timeout=60)

        if response.status_code == 200:
            result = response.json()
            text = result.get('response', '').strip()
            if text:
                logger.info(f'Ollama response received, length: {len(text)}')
                return text

        logger.error(f'Ollama error: {response.status_code} - {response.text}')
        return None

    except requests.exceptions.RequestException as e:
        logger.error(f'Ollama connection error: {e}')
        return None
    except Exception as e:
        logger.error(f'Ollama unexpected error: {e}')
        return None


def make_request_together(instructions: str, prompt: str, temperature: float = 0.7, max_tokens: int = 500) -> str | None:
    """
    Запрос к Together AI (есть бесплатный tier).
    """
    if not settings.TOGETHER_API_KEY:
        return None

    try:
        url = "https://api.together.xyz/v1/chat/completions"

        headers = {
            "Authorization": f"Bearer {settings.TOGETHER_API_KEY}",
            "Content-Type": "application/json"
        }

        data = {
            "model": "meta-llama/Llama-3.2-3B-Instruct-Turbo",  # Бесплатная модель
            "messages": [
                {"role": "system", "content": instructions},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        logger.info('Запрос к Together AI')
        response = requests.post(url, headers=headers, json=data, timeout=30)

        if response.status_code == 200:
            result = response.json()
            text = result.get('choices', [{}])[0].get('message', {}).get('content', '').strip()
            if text:
                logger.info(f'Together AI response received, length: {len(text)}')
                return text

        logger.error(f'Together AI error: {response.status_code} - {response.text}')
        return None

    except requests.exceptions.RequestException as e:
        logger.error(f'Together AI connection error: {e}')
        return None
    except Exception as e:
        logger.error(f'Together AI unexpected error: {e}')
        return None


def make_request(instructions: str, prompt: str, temperature: float = 0.7, max_tokens: int = 500) -> str | None:
    """
    Синхронный запрос к AI API с автоматическим fallback.
    
    Автоматически выбирает между доступными провайдерами в порядке приоритета:
    1. Ollama (локальная LLM, если USE_LOCAL_LLM=True)
    2. Together AI (бесплатный tier)
    3. OpenAI (основной провайдер)
    
    Args:
        instructions: Системные инструкции для AI
        prompt: Пользовательский запрос
        temperature: Температура генерации (0.0-1.0)
        max_tokens: Максимальное количество токенов в ответе
        
    Returns:
        Сгенерированный текст или None в случае ошибки
    """

    # 1. Ollama (если включена локальная LLM)
    if settings.USE_LOCAL_LLM:
        logger.info("Используем локальную LLM (Ollama)")
        result = make_request_ollama(instructions, prompt, temperature, max_tokens)
        if result:
            return result
        logger.warning("Ollama недоступна, пробуем Together AI")

    # 2. Together AI (бесплатная альтернатива)
    if settings.TOGETHER_API_KEY:
        logger.info("Пробуем Together AI (бесплатный tier)")
        result = make_request_together(instructions, prompt, temperature, max_tokens)
        if result:
            return result
        logger.warning("Together AI недоступен, переключаемся на OpenAI")

    # 3. OpenAI (основной провайдер)
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
    *_, arg_prompt, arg_text = sys.argv
    
    result = make_request(arg_prompt, arg_text)
    if result:
        print(result)
    else:
        print("Ошибка: не удалось получить ответ от AI")