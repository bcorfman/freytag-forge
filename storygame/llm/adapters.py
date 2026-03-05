from __future__ import annotations

import json
import os
import socket
import urllib.error
import urllib.parse
import urllib.request
from typing import Protocol

from storygame.llm.context import NarrationContext
from storygame.llm.prompts import build_prompt, build_prompt_text


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
    def __init__(
        self,
        model: str | None = None,
        timeout: float | None = None,
        base_url: str | None = None,
    ) -> None:
        env_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        env_timeout = float(os.getenv("OPENAI_TIMEOUT", "10.0"))
        env_base_url = os.getenv(
            "OPENAI_BASE_URL",
            "https://api.openai.com/v1/chat/completions",
        )
        self.model = model if model is not None else env_model
        self.timeout = timeout if timeout is not None else env_timeout
        self.base_url = base_url if base_url is not None else env_base_url
        self.api_key = os.getenv("OPENAI_API_KEY", "")

    def generate(self, context: NarrationContext) -> str:
        if not self.api_key:
            raise RuntimeError("OpenAI adapter requires OPENAI_API_KEY environment variable.")
        payload = build_prompt(context)
        request = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": payload["system"]},
                {"role": "user", "content": payload["user"]},
            ],
            "temperature": float(os.getenv("OPENAI_TEMPERATURE", "0.2")),
            "max_tokens": int(os.getenv("OPENAI_MAX_TOKENS", "512")),
        }
        http_request = urllib.request.Request(
            self.base_url,
            data=json.dumps(request).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json",
            },
        )
        try:
            with urllib.request.urlopen(http_request, timeout=self.timeout) as response:
                response_bytes = response.read()
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", errors="replace")
            raise RuntimeError(f"OpenAI API request failed: {exc.code} {detail}") from exc
        except urllib.error.URLError as exc:
            raise RuntimeError(
                f"Cannot reach OpenAI endpoint. Check OPENAI_BASE_URL and network. Error: {exc}."
            ) from exc
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("OpenAI API request failed.") from exc

        parsed = json.loads(response_bytes.decode("utf-8"))
        try:
            return parsed["choices"][0]["message"]["content"].strip()
        except Exception as exc:  # noqa: BLE001
            raise RuntimeError("OpenAI API response missing expected message content.") from exc


class OllamaAdapter:
    def __init__(
        self,
        model: str | None = None,
        timeout: float | None = None,
        base_url: str | None = None,
    ) -> None:
        env_model = os.getenv("OLLAMA_MODEL", "llama3.2")
        env_timeout = float(os.getenv("OLLAMA_TIMEOUT", "180.0"))
        env_base_url = os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/api/chat")
        self.model = model if model is not None else env_model
        self.timeout = timeout if timeout is not None else env_timeout
        self.base_url = base_url if base_url is not None else env_base_url

    def generate(self, context: NarrationContext) -> str:
        payload = build_prompt(context)
        request_common = {
            "temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.2")),
            "num_predict": int(os.getenv("OLLAMA_MAX_TOKENS", "512")),
        }
        endpoints = self._normalized_endpoints()
        attempt_errors: list[str] = []

        for endpoint in endpoints:
            if endpoint.endswith("/api/generate"):
                request = {
                    "model": self.model,
                    "prompt": f"{payload['system']}\n\n{payload['user']}",
                    "stream": False,
                    "options": request_common,
                }
            else:
                request = {
                    "model": self.model,
                    "messages": [
                        {"role": "system", "content": payload["system"]},
                        {"role": "user", "content": payload["user"]},
                    ],
                    "stream": False,
                    "options": request_common,
                }
            http_request = urllib.request.Request(
                endpoint,
                data=json.dumps(request).encode("utf-8"),
                method="POST",
                headers={"Content-Type": "application/json"},
            )
            try:
                with urllib.request.urlopen(http_request, timeout=self.timeout) as response:
                    response_bytes = response.read()
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                if exc.code in {404, 405, 500} and endpoint != endpoints[-1]:
                    attempt_errors.append(
                        f"{endpoint} -> HTTP {exc.code}: {detail}"
                    )
                    continue
                raise RuntimeError(f"Ollama API request failed: {exc.code} {detail}") from exc
            except urllib.error.URLError as exc:
                attempt_errors.append(
                    f"{endpoint} -> URL error: {exc}"
                )
                if endpoint == endpoints[-1]:
                    break
                continue
            except TimeoutError as exc:
                attempt_errors.append(
                    f"{endpoint} -> timeout after {self.timeout}s: {exc}"
                )
                if endpoint == endpoints[-1]:
                    break
                continue
            except socket.timeout as exc:
                attempt_errors.append(
                    f"{endpoint} -> socket timeout after {self.timeout}s: {exc}"
                )
                if endpoint == endpoints[-1]:
                    break
                continue
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError(
                    f"Ollama API request failed with {type(exc).__name__}: {exc}"
                ) from exc

            parsed = json.loads(response_bytes.decode("utf-8"))
            try:
                if "message" in parsed and "content" in parsed["message"]:
                    return parsed["message"]["content"].strip()
                if "response" in parsed:
                    return parsed["response"].strip()
                if "choices" in parsed:
                    return parsed["choices"][0]["message"]["content"].strip()
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError("Ollama API response had unexpected shape.") from exc
            raise RuntimeError("Ollama API response missing expected message content.")

        if attempt_errors:
            joined = " | ".join(attempt_errors)
            raise RuntimeError(
                "Ollama API request failed across endpoints. "
                f"model={self.model}. attempts={joined}. "
                "If the model is not installed, set OLLAMA_MODEL to one from /api/tags."
            )
        raise RuntimeError("Ollama API request failed with no endpoint diagnostics.")

    def _normalized_endpoints(self) -> tuple[str, ...]:
        base = self.base_url.rstrip("/")
        if base.endswith("/api/chat"):
            primary = base
            fallback = f"{base[:-8]}/api/generate"
        elif base.endswith("/api/generate"):
            primary = base
            fallback = f"{base[:-13]}/api/chat"
        elif base.endswith("/v1/chat/completions"):
            primary = base
            fallback = f"{base[:-20]}/api/chat"
        else:
            primary = f"{base}/api/chat"
            fallback = f"{base}/api/generate"

        expanded_endpoints: list[str] = [primary, fallback]
        for endpoint in (primary, fallback):
            parsed = urllib.parse.urlsplit(endpoint)
            host = parsed.hostname
            if host in {"localhost", "127.0.0.1"}:
                expanded_endpoints.append(
                    urllib.parse.urlunsplit(
                        (parsed.scheme, parsed.netloc.replace(host, "127.0.0.1"), parsed.path, "", ""),
                    )
                )
                expanded_endpoints.append(
                    urllib.parse.urlunsplit(
                        (parsed.scheme, parsed.netloc.replace(host, "localhost"), parsed.path, "", ""),
                    )
                )
                expanded_endpoints.append(
                    urllib.parse.urlunsplit(
                        (parsed.scheme, parsed.netloc.replace(host, "host.docker.internal"), parsed.path, "", ""),
                    )
                )

        # dedupe while preserving order
        unique_endpoints: list[str] = []
        for endpoint in expanded_endpoints:
            if endpoint not in unique_endpoints:
                unique_endpoints.append(endpoint)
        return tuple(unique_endpoints)


def describe_prompt(context: NarrationContext) -> str:
    return build_prompt_text(context)
