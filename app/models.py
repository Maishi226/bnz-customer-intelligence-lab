from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class CampaignRequest(BaseModel):
    product: str = Field(min_length=3, max_length=4000)
    brief: str = Field(default="", max_length=4000)
    channel: str = Field(default="BNZ app notification", max_length=120)
    timing: str = Field(default="When relevant", max_length=200)
    segment_ids: list[int] = Field(default_factory=list, max_length=6)
    persona_count: int = Field(default=5, ge=3, le=8)


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=2000)
    session_id: str = Field(min_length=1, max_length=100)
    context: dict[str, Any] = Field(default_factory=dict)


class Segment(BaseModel):
    segment_id: int
    segment_name: str
    customer_count: int = 0
    average_confidence: float = 0
    customers: list[dict[str, Any]] = Field(default_factory=list)
    source: str = "fallback"

