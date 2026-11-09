from langchain_anthropic import ChatAnthropic

from app.config import get_settings


def get_llm() -> ChatAnthropic:
    """Build the chat model from LLM_MODEL. No sampling parameters, the API rejects them."""
    settings = get_settings()
    options = {
        "model": settings.llm_model,
        "api_key": settings.anthropic_api_key,
        "max_tokens": 4096,
    }
    if settings.llm_model.startswith("claude-sonnet-5"):
        options["thinking"] = {"type": "between_tools"}
    return ChatAnthropic(**options)
