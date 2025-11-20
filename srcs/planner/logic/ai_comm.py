import logging
from typing import Optional, List, Any, Dict
from django.conf import settings
import requests

logger = logging.getLogger(__name__)


def send_text_to_ai(
    user_message: str,
    system_message: Optional[str] = None,
    max_tokens: Optional[int] = 1500,
    temperature: float = 0.0,
    stop: Optional[List[str]] = None,
    timeout: int = 30,
) -> str:
    """Send the provided text message to an external AI (Azure OpenAI style) and return the response text.

    Parameters:
    - user_message: the user content to send
    - system_message: optional system instruction to guide the model
    - max_tokens: optional hard cap for response size
    - temperature: sampling temperature (0.0 for deterministic)
    - stop: optional list of stop sequences
    - timeout: HTTP request timeout in seconds

    If required AI settings are not present in `settings`, the original message is returned unchanged.
    """
    api_url = getattr(settings, 'AI_API_URL', None)
    api_key = getattr(settings, 'AI_API_KEY', None)
    api_version = getattr(settings, 'AI_API_VERSION', None)
    deployment_name = getattr(settings, 'AI_DEPLOYMENT_NAME', None)

    if not all([api_url, api_key, api_version, deployment_name]):
        logger.warning('AI settings not configured; returning original text')
        return user_message

    headers = {
        'api-key': api_key,
        'Content-Type': 'application/json'
    }
    params: Dict[str, Any] = {
        'api-version': api_version
    }

    messages: List[Dict[str, str]] = []
    if system_message:
        messages.append({'role': 'system', 'content': system_message})
    messages.append({'role': 'user', 'content': user_message})

    data: Dict[str, Any] = {
        'messages': messages,
        'temperature': float(temperature)
    }

    if max_tokens is not None:
        data['max_tokens'] = int(max_tokens)
    if stop:
        data['stop'] = stop

    try:
        logger.debug('Sending AI request (deployment=%s, api_url=%s)', deployment_name, api_url)
        resp = requests.post(
            f"{api_url}/openai/deployments/{deployment_name}/chat/completions",
            headers=headers,
            params=params,
            json=data,
            timeout=timeout,
        )
        resp.raise_for_status()
        j = resp.json()

        # Defensive extraction for different response shapes
        try:
            # Azure-style chat completions
            return j['choices'][0]['message']['content']
        except Exception:
            try:
                # Fallback to common completions shape
                return j['choices'][0].get('text', user_message)
            except Exception:
                logger.exception('Unexpected AI response format')
                return user_message
    except Exception:
        logger.exception('AI request failed')
        return user_message
