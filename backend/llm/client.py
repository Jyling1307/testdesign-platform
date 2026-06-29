"""LLM client using LangChain ChatAnthropic for ZhipuAI GLM endpoint."""

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import SystemMessage, HumanMessage

from config import settings


def get_chat_model(temperature: float = 0.7) -> ChatAnthropic:
    return ChatAnthropic(
        model=settings.LLM_MODEL,
        api_key=settings.LLM_API_KEY,
        base_url=settings.LLM_BASE_URL,
        temperature=temperature,
        max_tokens=4096,
    )


def chat(system_prompt: str, user_message: str, temperature: float = 0.7) -> str:
    """Non-streaming LLM call. Returns response text."""
    llm = get_chat_model(temperature)
    response = llm.invoke([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ])
    return response.content


async def stream_chat(system_prompt: str, user_message: str, temperature: float = 0.7):
    """Async streaming LLM call. Yields text chunks."""
    llm = get_chat_model(temperature)
    async for chunk in llm.astream([
        SystemMessage(content=system_prompt),
        HumanMessage(content=user_message),
    ]):
        if chunk.content:
            yield chunk.content
