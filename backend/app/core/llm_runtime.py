from contextvars import ContextVar
from dataclasses import dataclass

import anthropic

from app.config import settings


@dataclass(frozen=True)
class LlmModelConfig:
    id: str
    provider: str
    label: str
    supports_vision: bool = True


DEEPSEEK_MODEL = "deepseek-v4-pro"

MODEL_OPTIONS: dict[str, LlmModelConfig] = {
    "claude-sonnet-5-5": LlmModelConfig("claude-sonnet-5-5", "anthropic", "Claude Sonnet 5.5"),
    "claude-opus-5-5": LlmModelConfig("claude-opus-5-5", "anthropic", "Claude Opus 5.5"),
    DEEPSEEK_MODEL: LlmModelConfig(DEEPSEEK_MODEL, "deepseek", "DeepSeek V4 Pro", False),
}

# Server-side refusal fallback: the API re-runs a declined request on a
# recommended fallback model inside the same call.
FALLBACK_BETA = "server-side-fallback-2026-07-01"

_request_provider: ContextVar[str] = ContextVar("request_llm_provider", default="claude")


def set_request_llm_provider(provider: str | None):
    normalized = provider if provider in {"claude", "deepseek"} else "claude"
    return _request_provider.set(normalized)


def reset_request_llm_provider(token) -> None:
    _request_provider.reset(token)


def selected_provider() -> str:
    return _request_provider.get()


def selected_model_id(default_model: str) -> str:
    return DEEPSEEK_MODEL if selected_provider() == "deepseek" else default_model


def selected_model_config(default_model: str) -> LlmModelConfig:
    model_id = selected_model_id(default_model)
    return MODEL_OPTIONS.get(model_id) or LlmModelConfig(model_id, "anthropic", model_id)


def create_messages_client(default_model: str) -> tuple[anthropic.Anthropic, str]:
    config = selected_model_config(default_model)
    if config.provider == "deepseek":
        if not settings.deepseek_api_key:
            raise ValueError("DEEPSEEK_API_KEY is not set.")
        return (
            anthropic.Anthropic(
                api_key=settings.deepseek_api_key,
                base_url=settings.deepseek_anthropic_base_url,
            ),
            config.id,
        )

    if not settings.anthropic_api_key:
        raise ValueError("ANTHROPIC_API_KEY is not set.")
    return anthropic.Anthropic(api_key=settings.anthropic_api_key), config.id


class LlmResponseError(ValueError):
    """The model returned no usable text (refusal, truncation, empty output)."""


def create_text_message(
    default_model: str,
    *,
    system: str,
    messages: list[dict],
    max_tokens: int,
    effort: str | None = None,
) -> str:
    """Send one Messages request and return the concatenated text blocks.

    Claude 5.x models always think, so the response may start with thinking
    blocks; only ``text`` blocks are returned. Claude requests are streamed so
    large ``max_tokens`` values do not hit HTTP timeouts.
    """
    client, model = create_messages_client(default_model)
    config = selected_model_config(default_model)
    params: dict = {
        "model": model,
        "max_tokens": max_tokens,
        "system": system,
        "messages": messages,
    }

    if config.provider == "anthropic":
        if effort:
            params["output_config"] = {"effort": effort}
        params["extra_headers"] = {"anthropic-beta": FALLBACK_BETA}
        params["extra_body"] = {"fallbacks": "default"}
        with client.messages.stream(**params) as stream:
            response = stream.get_final_message()
    else:
        response = client.messages.create(**params)

    if response.stop_reason == "refusal":
        category = getattr(getattr(response, "stop_details", None), "category", None)
        raise LlmResponseError(f"Model declined the request (category: {category}).")

    text = "".join(
        block.text for block in response.content if getattr(block, "type", None) == "text"
    ).strip()
    if response.stop_reason == "max_tokens":
        raise LlmResponseError(f"Model output hit max_tokens={max_tokens}.")
    if not text:
        raise LlmResponseError("Model returned no text output.")
    return text
