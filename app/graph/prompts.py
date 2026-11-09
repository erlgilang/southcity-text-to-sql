from functools import cache
from pathlib import Path

from langchain_core.messages import BaseMessage
from langchain_core.prompts import ChatPromptTemplate

PROMPT_DIR = Path(__file__).resolve().parents[1] / "prompts"


@cache
def _template(name: str) -> ChatPromptTemplate:
    system = (PROMPT_DIR / f"{name}.md").read_text(encoding="utf-8")
    return ChatPromptTemplate.from_messages([("system", system), ("human", "{human}")])


def build_messages(name: str, human: str, **variables: str) -> list[BaseMessage]:
    return _template(name).invoke({**variables, "human": human}).to_messages()


def escape_tags(text: str) -> str:
    """Stop text written by a user from closing or opening the XML tags around it."""
    return text.replace("<", "&lt;").replace(">", "&gt;")


def format_history(turns: list[tuple[str, str]]) -> str:
    return "\n".join(
        f"Pengguna: {escape_tags(question)}\nAsisten: {escape_tags(answer)}"
        for question, answer in turns
    )
