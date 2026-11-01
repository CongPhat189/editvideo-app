from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class GenerateVideoRequest(BaseModel):
    prompt: str | None = None
    selectedVideos: list[int] | None = Field(default_factory=list)
    localFiles: list[Any] | None = Field(default_factory=list)


class SchedulingCreateRequest(BaseModel):
    selectedDate: int | str | None = None
    title: str | None = None
    time: str | None = None
    channels: list[str] | None = None


class PublishingRequest(BaseModel):
    content: str | None = None
    platforms: list[str] | None = None
