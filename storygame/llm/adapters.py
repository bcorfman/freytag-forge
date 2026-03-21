from __future__ import annotations

import json
import os
import socket
import time
import urllib.error
import urllib.parse
import urllib.request
from typing import Protocol
from uuid import uuid4

from storygame.llm.context import NarrationContext
from storygame.llm.prompts import build_prompt, build_prompt_text


class Narrator(Protocol):
    def generate(self, context: NarrationContext) -> str: ...


class SilentNarrator:
    def generate(self, context: NarrationContext) -> str:
        return ""


def _max_tokens_for_context(context: NarrationContext, env_var: str, default_turn_limit: int, default_opening_limit: int) -> int:
    configured = os.getenv(env_var, "").strip()
    if configured:
        return int(configured)
    if context.beat == "setup_scene":
        return default_opening_limit
    return default_turn_limit


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
            "max_tokens": _max_tokens_for_context(context, "OPENAI_MAX_TOKENS", 512, 1100),
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
        max_tokens = _max_tokens_for_context(context, "OLLAMA_MAX_TOKENS", 512, 1100)
        request_common = {
            "temperature": float(os.getenv("OLLAMA_TEMPERATURE", "0.2")),
            "num_predict": max_tokens,
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
                    attempt_errors.append(f"{endpoint} -> HTTP {exc.code}: {detail}")
                    continue
                raise RuntimeError(f"Ollama API request failed: {exc.code} {detail}") from exc
            except urllib.error.URLError as exc:
                attempt_errors.append(f"{endpoint} -> URL error: {exc}")
                if endpoint == endpoints[-1]:
                    break
                continue
            except TimeoutError as exc:
                attempt_errors.append(f"{endpoint} -> timeout after {self.timeout}s: {exc}")
                if endpoint == endpoints[-1]:
                    break
                continue
            except Exception as exc:  # noqa: BLE001
                if isinstance(exc, socket.timeout):
                    attempt_errors.append(f"{endpoint} -> socket timeout after {self.timeout}s: {exc}")
                    if endpoint == endpoints[-1]:
                        break
                    continue
                raise RuntimeError(f"Ollama API request failed with {type(exc).__name__}: {exc}") from exc

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


class CloudflareWorkersAIAdapter:
    USER_AGENT = "FreytagForgeDemo/1.0"

    def __init__(
        self,
        worker_url: str | None = None,
        token: str | None = None,
        timeout: float | None = None,
        retries: int | None = None,
        retry_backoff_ms: int | None = None,
    ) -> None:
        env_worker_url = os.getenv("CLOUDFLARE_WORKER_URL", "")
        env_token = os.getenv("CLOUDFLARE_WORKER_TOKEN", "")
        env_timeout = os.getenv("CLOUDFLARE_TIMEOUT", "20.0")
        env_retries = os.getenv("CLOUDFLARE_RETRIES", "1")
        env_retry_backoff_ms = os.getenv("CLOUDFLARE_RETRY_BACKOFF_MS", "250")
        self.worker_url = worker_url.strip() if worker_url is not None else env_worker_url.strip()
        self.token = token.strip() if token is not None else env_token.strip()
        self.timeout = timeout if timeout is not None else float(env_timeout.strip())
        self.retries = retries if retries is not None else int(env_retries.strip())
        self.retry_backoff_ms = (
            retry_backoff_ms if retry_backoff_ms is not None else int(env_retry_backoff_ms.strip())
        )

    def generate(self, context: NarrationContext) -> str:
        if not self.worker_url:
            raise RuntimeError("Cloudflare adapter requires CLOUDFLARE_WORKER_URL environment variable.")

        payload = build_prompt(context)
        trace_id = uuid4().hex
        request_payload = {
            "system": payload["system"],
            "user": payload["user"],
            "trace_id": trace_id,
            "session_id": "",
        }
        headers = {
            "Content-Type": "application/json",
            "User-Agent": self.USER_AGENT,
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        http_request = urllib.request.Request(
            self.worker_url,
            data=json.dumps(request_payload).encode("utf-8"),
            method="POST",
            headers=headers,
        )
        attempt = 0
        while True:
            try:
                with urllib.request.urlopen(http_request, timeout=self.timeout) as response:
                    response_bytes = response.read()
                break
            except urllib.error.HTTPError as exc:
                detail = exc.read().decode("utf-8", errors="replace")
                if exc.code == 429 and ("AI_QUOTA_EXCEEDED" in detail or "quota" in detail.lower()):
                    raise RuntimeError(f"Cloudflare Workers AI request failed: 429 AI_QUOTA_EXCEEDED {detail}") from exc
                if 500 <= exc.code <= 599 and attempt < self.retries:
                    self._sleep_before_retry(attempt)
                    attempt += 1
                    continue
                raise RuntimeError(f"Cloudflare Workers AI request failed: {exc.code} {detail}") from exc
            except urllib.error.URLError as exc:
                if attempt < self.retries:
                    self._sleep_before_retry(attempt)
                    attempt += 1
                    continue
                raise RuntimeError(f"Cannot reach Cloudflare Worker endpoint. Error: {exc}.") from exc
            except Exception as exc:  # noqa: BLE001
                if isinstance(exc, socket.timeout) and attempt < self.retries:
                    self._sleep_before_retry(attempt)
                    attempt += 1
                    continue
                raise RuntimeError("Cloudflare Workers AI request failed.") from exc

        parsed = json.loads(response_bytes.decode("utf-8"))
        narration = str(parsed.get("narration", "")).strip()
        if narration:
            return narration
        if "choices" in parsed:
            try:
                return str(parsed["choices"][0]["message"]["content"]).strip()
            except Exception as exc:  # noqa: BLE001
                raise RuntimeError("Cloudflare Workers AI response had unexpected shape.") from exc
        raise RuntimeError("Cloudflare Workers AI response missing expected narration content.")

    def _sleep_before_retry(self, attempt: int) -> None:
        delay_ms = self.retry_backoff_ms * (attempt + 1)
        if delay_ms <= 0:
            return
        time.sleep(delay_ms / 1000.0)


def describe_prompt(context: NarrationContext) -> str:
    return build_prompt_text(context)
