"""
Pydantic models for the API request / response contracts.
"""

from pydantic import BaseModel, Field


class ChatMessage(BaseModel):
    """A single chat message (user or assistant)."""
    role: str = Field(..., description="Either 'user' or 'assistant'")
    content: str = Field(..., description="Message text")


class ChatRequest(BaseModel):
    """Incoming chat request from the frontend."""
    message: str = Field(..., description="Current user message")
    history: list[ChatMessage] = Field(default_factory=list, description="Conversation history")
    api_key: str | None = Field(None, description="Optional user-provided Gemini API Key")


class ToolResult(BaseModel):
    """Result returned by an internal tool execution."""
    tool_name: str
    data: dict
