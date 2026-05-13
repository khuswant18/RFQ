"""Groq Client with key rotation, retry backoff, and latency logging."""
import os
import time
import json
import logging
from typing import List, Optional, Dict, Any

logger = logging.getLogger(__name__)


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

    def get_next_key(self, current_key: str) -> Optional[str]:
        """Get a different key than the current one (fallback on error)."""
        if len(self.keys) < 2:
            return None
        for key in self.keys:
            if key != current_key:
                return key
        return None


class GroqClient:
    """Groq API client with key rotation, exponential backoff, and mock mode."""

    MAX_RETRIES = 3
    RETRY_BASE_DELAY = 1.0  # seconds

    def __init__(self):
        # Load up to 5 Groq API keys from environment
        self.keys = []
        for i in range(1, 6):
            key = os.getenv(f"GROQ_API_KEY_{i}")
            if key and key.startswith("gsk_") and len(key) > 20:
                self.keys.append(key)

        if not self.keys:
            logger.warning("⚠️  No valid Groq API keys found. Using mock-only mode.")

        self.key_rotator = GroqKeyRotator(self.keys) if self.keys else None
        self.base_url = "https://api.groq.com/openai/v1"

    def _use_mock(self) -> bool:
        """Returns True if MOCK_GROQ is set to 'true' (case-insensitive)."""
        return os.getenv("MOCK_GROQ", "true").lower() == "true"

    def _make_request(self, api_key: str, payload: dict, timeout: int = 60) -> dict:
        """Make a single HTTP request to Groq with the given key."""
        import requests
        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }
        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=timeout,
        )
        response.raise_for_status()
        return response.json()

    def call(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = "llama3-70b-8192",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Synchronous Groq API call with exponential backoff retry."""
        if self._use_mock():
            return self._mock_call(system_prompt, user_prompt, model)

        if not self.key_rotator:
            raise RuntimeError("Groq API keys not configured and MOCK_GROQ is false.")

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        last_error = None
        api_key = self.key_rotator.get_key()

        for attempt in range(1, self.MAX_RETRIES + 1):
            t0 = time.time()
            try:
                result = self._make_request(api_key, payload)
                latency_ms = round((time.time() - t0) * 1000)
                content = result["choices"][0]["message"]["content"]
                usage = result.get("usage", {})
                logger.info(
                    "Groq call OK | model=%s attempt=%d latency=%dms "
                    "prompt_tokens=%s completion_tokens=%s",
                    model, attempt, latency_ms,
                    usage.get("prompt_tokens", "?"),
                    usage.get("completion_tokens", "?"),
                )
                return content

            except Exception as exc:
                latency_ms = round((time.time() - t0) * 1000)
                last_error = exc
                logger.warning(
                    "Groq call FAILED | attempt=%d/%d latency=%dms error=%s",
                    attempt, self.MAX_RETRIES, latency_ms, exc,
                )

                # On first failure, try the fallback key if available
                if attempt == 1:
                    fallback_key = self.key_rotator.get_next_key(api_key)
                    if fallback_key:
                        logger.info("Switching to fallback Groq API key.")
                        api_key = fallback_key

                if attempt < self.MAX_RETRIES:
                    delay = self.RETRY_BASE_DELAY * (2 ** (attempt - 1))  # 1s, 2s, 4s
                    logger.info("Retrying Groq in %.1fs...", delay)
                    time.sleep(delay)

        raise RuntimeError(f"Groq API failed after {self.MAX_RETRIES} attempts: {last_error}")

    def call_sync(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = "llama3-70b-8192",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Alias for call() — explicitly synchronous."""
        return self.call(system_prompt, user_prompt, model, temperature, max_tokens)

    async def call_async(
        self,
        system_prompt: str,
        user_prompt: str,
        model: str = "llama3-70b-8192",
        temperature: float = 0.7,
        max_tokens: int = 4096,
    ) -> str:
        """Async Groq API call with retry."""
        if self._use_mock():
            return self._mock_call(system_prompt, user_prompt, model)

        if not self.key_rotator:
            raise RuntimeError("Groq API keys not configured and MOCK_GROQ is false.")

        import aiohttp

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt},
            ],
            "temperature": temperature,
            "max_tokens": max_tokens,
        }

        api_key = self.key_rotator.get_key()
        last_error = None

        for attempt in range(1, self.MAX_RETRIES + 1):
            t0 = time.time()
            try:
                headers = {
                    "Authorization": f"Bearer {api_key}",
                    "Content-Type": "application/json",
                }
                async with aiohttp.ClientSession() as session:
                    async with session.post(
                        f"{self.base_url}/chat/completions",
                        headers=headers,
                        json=payload,
                        timeout=aiohttp.ClientTimeout(total=60),
                    ) as response:
                        response.raise_for_status()
                        result = await response.json()
                        latency_ms = round((time.time() - t0) * 1000)
                        content = result["choices"][0]["message"]["content"]
                        usage = result.get("usage", {})
                        logger.info(
                            "Groq async OK | model=%s attempt=%d latency=%dms "
                            "prompt_tokens=%s completion_tokens=%s",
                            model, attempt, latency_ms,
                            usage.get("prompt_tokens", "?"),
                            usage.get("completion_tokens", "?"),
                        )
                        return content
            except Exception as exc:
                last_error = exc
                logger.warning(
                    "Groq async FAILED | attempt=%d/%d error=%s", attempt, self.MAX_RETRIES, exc
                )
                if attempt == 1:
                    fallback_key = self.key_rotator.get_next_key(api_key)
                    if fallback_key:
                        api_key = fallback_key
                if attempt < self.MAX_RETRIES:
                    import asyncio
                    await asyncio.sleep(self.RETRY_BASE_DELAY * (2 ** (attempt - 1)))

        raise RuntimeError(f"Groq async API failed after {self.MAX_RETRIES} attempts: {last_error}")

    def call_vision(
        self,
        system_prompt: str,
        image_data: str,
        model: str = "llava-v1.5-7b-4096-preview",
    ) -> Dict[str, Any]:
        """Vision call to Groq for OCR/image understanding."""
        if self._use_mock():
            return self._mock_vision_call(system_prompt, image_data)

        if not self.key_rotator:
            raise RuntimeError("Groq API keys not configured and MOCK_GROQ is false.")

        api_key = self.key_rotator.get_key()
        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": "Extract all text from this image."},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/jpeg;base64,{image_data}"},
                        },
                    ],
                },
            ],
            "temperature": 0.1,
            "max_tokens": 4096,
        }

        last_error = None
        for attempt in range(1, self.MAX_RETRIES + 1):
            t0 = time.time()
            try:
                result = self._make_request(api_key, payload)
                latency_ms = round((time.time() - t0) * 1000)
                text = result["choices"][0]["message"]["content"]
                logger.info("Groq vision OK | latency=%dms", latency_ms)
                try:
                    parsed = json.loads(text)
                    return {
                        "extracted_text": parsed.get("extracted_text", text),
                        "confidence": parsed.get("confidence", 0.85),
                        "language_detected": parsed.get("language_detected", "en"),
                    }
                except json.JSONDecodeError:
                    return {
                        "extracted_text": text,
                        "confidence": 0.85,
                        "language_detected": "en",
                    }
            except Exception as exc:
                last_error = exc
                logger.warning("Groq vision FAILED | attempt=%d error=%s", attempt, exc)
                if attempt == 1:
                    fallback_key = self.key_rotator.get_next_key(api_key)
                    if fallback_key:
                        api_key = fallback_key
                if attempt < self.MAX_RETRIES:
                    time.sleep(self.RETRY_BASE_DELAY * (2 ** (attempt - 1)))

        logger.error("Groq vision failed after %d attempts: %s. Falling back to empty.", self.MAX_RETRIES, last_error)
        return {"extracted_text": "", "confidence": 0.0, "language_detected": "en"}

    # ==================== Mock Responses ====================

    def _mock_call(self, system_prompt: str, user_prompt: str, model: str) -> str:
        """Return a deterministic mock response for testing without API keys."""
        lower_prompt = user_prompt.lower()
        lower_system = system_prompt.lower()

        # Price extraction mock
        if "price" in lower_prompt and ("mcx" in lower_prompt or "steel" in lower_prompt):
            return '{"price_per_ton": 58000, "source": "mock", "as_of": "today"}'

        # OCR extraction mock
        if "ocr" in lower_system or ("extract" in lower_prompt and "image" in lower_prompt):
            return '{"extracted_text": "12mm Sariya Fe500 10 ton Surat", "confidence": 0.9, "language_detected": "mixed"}'

        # NER / entity extraction mock
        if "metallurgist" in lower_system or "extract" in lower_system or "ner" in lower_system:
            mock_entities = {
                "line_items": [
                    {
                        "item_id": 1,
                        "material_type": "TMT_Bar",
                        "is_code": "IS 1786:2008",
                        "grade": "Fe 500",
                        "shape": "Round",
                        "dimensions": {"diameter_mm": 12, "length_ft": 40},
                        "quantity": {"value": 10, "unit": "tons"},
                        "destination_pincode": "395006",
                        "destination_raw": "Surat",
                        "urgency": None,
                        "confidence_scores": {
                            "material_type": 0.95,
                            "grade": 0.92,
                            "quantity": 0.90,
                        },
                    }
                ],
                "language": "en",
                "is_sub_inquiry": False,
                "price_inclusive_gst": False,
                "overall_confidence": 0.92,
            }
            return json.dumps(mock_entities)

        # WhatsApp summary mock
        if "whatsapp" in lower_system or "whatsapp" in lower_prompt:
            return (
                "Dear Sir/Madam,\n\n"
                "Thank you for your enquiry. Please find attached our quotation.\n\n"
                "Quote Summary:\n"
                "- Material: TMT Bar Fe500 12mm\n"
                "- Quantity: 10 MT\n"
                "- Total: ₹6,84,400\n\n"
                "Quote PDF attached. Valid for 24 hours.\n\n"
                "Regards,\nDemo Steel Works"
            )

        # Default mock
        return '{"response": "Mock response from Groq"}'

    def _mock_vision_call(self, system_prompt: str, image_data: str) -> Dict[str, Any]:
        """Return a mock vision response for testing."""
        return {
            "extracted_text": "12mm Sariya Fe500 10 ton delivery to Sachin GIDC, Surat 394230",
            "confidence": 0.9,
            "language_detected": "mixed",
        }
