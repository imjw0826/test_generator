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
    "claude-sonnet-4-6": LlmModelConfig("claude-sonnet-4-6", "anthropic", "Claude Sonnet 4.6"),
    "claude-opus-4-7": LlmModelConfig("claude-opus-4-7", "anthropic", "Claude Opus 4.7"),
    DEEPSEEK_MODEL: LlmModelConfig(DEEPSEEK_MODEL, "deepseek", "DeepSeek V4 Pro", False),
}

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
