from __future__ import annotations

from pydantic import BaseModel


class TranscriptionSegment(BaseModel):
	start: float
	end: float
	text: str


class TranscriptionResult(BaseModel):
	text: str
	language: str | None = None
	segments: list[TranscriptionSegment] = []
	provider: str = ""


