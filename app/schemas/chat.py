from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints


class ChatMessage(BaseModel):
    role: Literal["user", "assistant"]
    content: Annotated[
        str,
        StringConstraints(strip_whitespace=True, min_length=1, max_length=4000),
    ]


class ChatRequest(BaseModel):
    messages: list[ChatMessage] = Field(min_length=1, max_length=20)


class ChatResponse(BaseModel):
    reply: str
