from __future__ import annotations

import os
from typing import Protocol

from storygame.llm.context import NarrationContext
from storygame.llm.prompts import build_prompt_text


class Narrator(Protocol):
    def generate(self, context: NarrationContext) -> str:
        ...


class MockNarrator:
    def __init__(self, prefix: str = "") -> None:
        self.prefix = prefix

    def generate(self, context: NarrationContext) -> str:
        base = f"{self.prefix}{context.beat.title()} beat at {context.room_name}."
        return base + " " + context.goal


class SilentNarrator:
    def generate(self, context: NarrationContext) -> str:
        return ""


class OpenAIAdapter:
    def __init__(self, model: str | None = None, timeout: float | None = None) -> None:
        env_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        env_timeout = float(os.getenv("OPENAI_TIMEOUT", "10.0"))
        self.model = model if model is not None else env_model
        self.timeout = timeout if timeout is not None else env_timeout
        self.api_key = os.getenv("OPENAI_API_KEY", "")

    def generate(self, context: NarrationContext) -> str:
        if not self.api_key:
            raise RuntimeError("OpenAI adapter requires OPENAI_API_KEY environment variable.")
        raise RuntimeError("OpenAI adapter is a placeholder in this milestone and is not wired yet.")


def describe_prompt(context: NarrationContext) -> str:
    return build_prompt_text(context)
