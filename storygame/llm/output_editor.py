from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from typing import Protocol


class OutputEditor(Protocol):
    def review_opening(self, lines: list[str], active_goal: str) -> list[str]: ...

    def review_turn(self, lines: list[str], active_goal: str, turn_index: int, debug: bool = False) -> list[str]: ...


class OpenAIOutputEditor:
    def __init__(self) -> None:
        self._api_key = os.getenv("OPENAI_API_KEY", "")
        self._base_url = os.getenv("OPENAI_BASE_URL", "https://api.openai.com/v1/chat/completions")
        self._model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self._timeout = float(os.getenv("OPENAI_TIMEOUT", "10.0"))

    def review_opening(self, lines: list[str], active_goal: str) -> list[str]:
        return self._review_with_llm(lines, active_goal, opening=True)

    def review_turn(self, lines: list[str], active_goal: str, turn_index: int, debug: bool = False) -> list[str]:
        if debug:
            return lines
        return self._review_with_llm(lines, active_goal, opening=False)

    def _review_with_llm(self, lines: list[str], active_goal: str, opening: bool) -> list[str]:
        if not self._api_key:
            return lines

        system = (
            "You are a strict fiction output editor. Rewrite minimally and return JSON only: "
            "{\"lines\": [\"...\"]}. Do not invent facts. Remove awkward repetition."
        )
        if opening:
            instruction = (
                "Opening scene rules: exactly 3-4 paragraphs; no room-block format lines; no meta wording; "
                "natural prose and second-person framing where needed."
            )
        else:
            instruction = (
                "Turn rules: keep room block as provided first; "
                "avoid repeating full game goals unless naturally prompted."
            )
        user = json.dumps({"instruction": instruction, "active_goal": active_goal, "lines": lines}, ensure_ascii=True)
        request = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "temperature": 0.0,
            "max_tokens": 512,
        }
        http_request = urllib.request.Request(
            self._base_url,
            data=json.dumps(request).encode("utf-8"),
            method="POST",
            headers={"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(http_request, timeout=self._timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
                content = str(payload["choices"][0]["message"]["content"]).strip()
                parsed = json.loads(content)
                reviewed = [str(line).strip() for line in parsed.get("lines", []) if str(line).strip()]
                if reviewed:
                    return reviewed[:4] if opening else reviewed
        except Exception:  # noqa: BLE001
            pass
        return lines


class OllamaOutputEditor:
    def __init__(self) -> None:
        self._base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/api/chat")
        self._model = os.getenv("OLLAMA_MODEL", "llama3.2")
        self._timeout = float(os.getenv("OLLAMA_TIMEOUT", "180.0"))

    def review_opening(self, lines: list[str], active_goal: str) -> list[str]:
        return self._review_with_llm(lines, active_goal, opening=True)

    def review_turn(self, lines: list[str], active_goal: str, turn_index: int, debug: bool = False) -> list[str]:
        if debug:
            return lines
        return self._review_with_llm(lines, active_goal, opening=False)

    def _review_with_llm(self, lines: list[str], active_goal: str, opening: bool) -> list[str]:
        instruction = (
            "Opening scene: return 3-4 polished paragraphs only."
            if opening
            else "Turn output: keep room block first and reduce repetitive goal reminders."
        )
        request = {
            "model": self._model,
            "messages": [
                {"role": "system", "content": "Strict fiction editor. Return JSON only with key 'lines'."},
                {
                    "role": "user",
                    "content": json.dumps(
                        {"instruction": instruction, "active_goal": active_goal, "lines": lines},
                        ensure_ascii=True,
                    ),
                },
            ],
            "stream": False,
            "options": {"temperature": 0.0, "num_predict": 512},
        }
        http_request = urllib.request.Request(
            self._base_url,
            data=json.dumps(request).encode("utf-8"),
            method="POST",
            headers={"Content-Type": "application/json"},
        )
        try:
            with urllib.request.urlopen(http_request, timeout=self._timeout) as response:
                payload = json.loads(response.read().decode("utf-8"))
                content = ""
                if "message" in payload and "content" in payload["message"]:
                    content = str(payload["message"]["content"]).strip()
                elif "response" in payload:
                    content = str(payload["response"]).strip()
                if content:
                    parsed = json.loads(content)
                    reviewed = [str(line).strip() for line in parsed.get("lines", []) if str(line).strip()]
                    if reviewed:
                        return reviewed[:4] if opening else reviewed
        except Exception:  # noqa: BLE001
            pass
        return lines


def build_output_editor(mode: str) -> OutputEditor:
    if mode == "openai":
        return OpenAIOutputEditor()
    if mode == "ollama":
        return OllamaOutputEditor()
    raise ValueError("Output editor requires LLM mode: openai or ollama.")
