"""Shared schema for chat messages."""

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single turn in the chat history."""

    role: str = Field(..., description="The role of the message sender (e.g., 'user', 'assistant').")
    content: str = Field(..., description="The text content of the message.")
