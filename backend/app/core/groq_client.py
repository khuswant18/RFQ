"""Groq Client with key rotation and real API calls."""
import asyncio
import json
import logging
import os
import time
from typing import List, Optional, Dict, Any
from dotenv import load_dotenv

load_dotenv()


class GroqKeyRotator:
    """Round-robin key rotation with per-key request count tracking."""

    def __init__(self, keys: List[str]):
        self.keys = keys
        self.current_index = 0
        self.request_counts = {k: 0 for k in keys}

    def get_key(self) -> str:
        key = self.keys[self.current_index % len(self.keys)]
        self.current_index += 1
        self.request_counts[key] += 1
        return key


class GroqClient:
    """Groq API client with key rotation and sync/async support."""

    def __init__(self):
        # Load up to 5 Groq API keys from environment
        self.keys = []
        for i in range(1, 6):
            key = os.getenv(f"GROQ_API_KEY_{i}")
            if key:
                self.keys.append(key)

        if not self.keys:
            raise RuntimeError("Groq API keys not configured. Set GROQ_API_KEY_1..5.")

        self.key_rotator = GroqKeyRotator(self.keys) if self.keys else None
        self.base_url = "https://api.groq.com/openai/v1"
        self.logger = logging.getLogger("srip.groq")

    def _key_candidates(self) -> List[str]:
        if not self.keys:
            return []
        primary = self.keys[0]
        secondary = self.keys[1] if len(self.keys) > 1 else None
        rest = [k for k in self.keys if k not in {primary, secondary}]
        candidates = [primary]
        if secondary:
            candidates.append(secondary)
        candidates.extend(rest)
        return candidates

    def _log_call(self, model: str, latency_ms: float, usage: Dict[str, Any]):
        total_tokens = usage.get("total_tokens") if usage else None
        self.logger.info(
            "groq_call model=%s latency_ms=%.2f total_tokens=%s",
            model,
            latency_ms,
            total_tokens,
        )

    def call(self, system_prompt: str, user_prompt: str,
             model: str = "llama-3.3-70b-versatile", temperature: float = 0.7,
             max_tokens: int = 4096) -> str:
        """Make a synchronous call to Groq API."""
        if not self.keys:
            raise RuntimeError("Groq API keys not configured.")

        import requests

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        last_error = None
        for attempt in range(1, 4):
            for api_key in self._key_candidates():
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                start = time.time()
                try:
                    response = requests.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=60
                    )
                    response.raise_for_status()
                    result = response.json()
                    latency_ms = (time.time() - start) * 1000
                    self._log_call(model, latency_ms, result.get("usage", {}))
                    return result["choices"][0]["message"]["content"]
                except Exception as exc:
                    last_error = exc
            time.sleep(2 ** (attempt - 1))

        raise RuntimeError(f"Groq API call failed after retries: {last_error}")

    def call_sync(self, system_prompt: str, user_prompt: str,
                  model: str = "llama-3.3-70b-versatile", temperature: float = 0.7,
                  max_tokens: int = 4096) -> str:
        """Alias for call() — explicitly synchronous."""
        return self.call(system_prompt, user_prompt, model, temperature, max_tokens)

    async def call_async(self, system_prompt: str, user_prompt: str,
                          model: str = "llama-3.3-70b-versatile", temperature: float = 0.7,
                          max_tokens: int = 4096) -> str:
        """Make an async call to Groq API."""
        if not self.keys:
            raise RuntimeError("Groq API keys not configured.")

        import aiohttp

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        last_error = None
        for attempt in range(1, 4):
            for api_key in self._key_candidates():
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                start = time.time()
                try:
                    async with aiohttp.ClientSession() as session:
                        async with session.post(
                            f"{self.base_url}/chat/completions",
                            headers=headers,
                            json=payload,
                            timeout=aiohttp.ClientTimeout(total=60)
                        ) as response:
                            response.raise_for_status()
                            result = await response.json()
                            latency_ms = (time.time() - start) * 1000
                            self._log_call(model, latency_ms, result.get("usage", {}))
                            return result["choices"][0]["message"]["content"]
                except Exception as exc:
                    last_error = exc
            await asyncio.sleep(2 ** (attempt - 1))

        raise RuntimeError(f"Groq API call failed after retries: {last_error}")

    def call_vision(self, system_prompt: str, image_data: str,
                    model: str = "llama-3.2-11b-vision-preview") -> Dict[str, Any]:
        """Make a vision call to Groq API for image understanding."""
        if not self.keys:
            raise RuntimeError("Groq API keys not configured.")

        import requests

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract all text from this image."},
                        {"type": "image_url", "image_url": {"url": f"data:image/jpeg;base64,{image_data}"}}
                    ]
                }
            ],
            "temperature": 0.1,
            "max_tokens": 4096
        }

        last_error = None
        for attempt in range(1, 4):
            for api_key in self._key_candidates():
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json"
                }
                start = time.time()
                try:
                    response = requests.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=60
                    )
                    response.raise_for_status()
                    result = response.json()
                    latency_ms = (time.time() - start) * 1000
                    self._log_call(model, latency_ms, result.get("usage", {}))
                    text = result["choices"][0]["message"]["content"]

                    try:
                        parsed = json.loads(text)
                        return {
                            "extracted_text": parsed.get("extracted_text", text),
                            "confidence": parsed.get("confidence", 0.85),
                            "language_detected": parsed.get("language_detected", "en")
                        }
                    except json.JSONDecodeError:
                        return {
                            "extracted_text": text,
                            "confidence": 0.85,
                            "language_detected": "en"
                        }
                except Exception as exc:
                    last_error = exc
            time.sleep(2 ** (attempt - 1))

        print(f"Groq vision call failed after retries: {last_error}. Falling back to Tesseract.")
        return {
            "extracted_text": "",
            "confidence": 0.0,
            "language_detected": "en"
        }

