from typing import Literal

from pydantic import BaseModel, Field


class Classification(BaseModel):
    intent: Literal["sql_query", "chitchat", "clarify", "refuse"]
    standalone_question: str = Field(description="The question rewritten so it needs no history")
    relevant_tables: list[str] = Field(default_factory=list)
    message: str = Field(
        default="", description="Clarifying question, refusal, or a note about missing data"
    )


class GeneratedSql(BaseModel):
    sql: str = Field(description="Exactly one SELECT statement")
    money_columns: list[str] = Field(
        default_factory=list, description="Output columns that hold Rupiah amounts"
    )
