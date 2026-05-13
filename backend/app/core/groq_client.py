"""Groq Client with key rotation and mock support."""
import os
import time
import json
from typing import List, Optional, Dict, Any


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
    """Groq API client with key rotation, sync/async support, and mock mode."""

    def __init__(self):
        # Load up to 5 Groq API keys from environment
        self.keys = []
        for i in range(1, 6):
            key = os.getenv(f"GROQ_API_KEY_{i}")
            if key:
                self.keys.append(key)

        if not self.keys:
            print("⚠️  No Groq API keys found. Using mock-only mode.")

        self.key_rotator = GroqKeyRotator(self.keys) if self.keys else None
        self.base_url = "https://api.groq.com/openai/v1"

    def _use_mock(self) -> bool:
        return os.getenv("MOCK_GROQ", "true").lower() == "true"

    def call(self, system_prompt: str, user_prompt: str,
             model: str = "llama3-70b-8192", temperature: float = 0.7,
             max_tokens: int = 4096) -> str:
        """Make a synchronous call to Groq API."""
        # Check mock mode FIRST — before touching key_rotator
        if self._use_mock():
            return self._mock_call(system_prompt, user_prompt, model)

        if not self.key_rotator:
            raise RuntimeError("Groq API keys not configured and MOCK_GROQ is false.")

        import requests

        api_key = self.key_rotator.get_key()

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        response = requests.post(
            f"{self.base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )

        response.raise_for_status()
        result = response.json()

        return result["choices"][0]["message"]["content"]

    def call_sync(self, system_prompt: str, user_prompt: str,
                  model: str = "llama3-70b-8192", temperature: float = 0.7,
                  max_tokens: int = 4096) -> str:
        """Alias for call() — explicitly synchronous."""
        return self.call(system_prompt, user_prompt, model, temperature, max_tokens)

    async def call_async(self, system_prompt: str, user_prompt: str,
                          model: str = "llama3-70b-8192", temperature: float = 0.7,
                          max_tokens: int = 4096) -> str:
        """Make an async call to Groq API."""
        # Check mock mode FIRST
        if self._use_mock():
            return self._mock_call(system_prompt, user_prompt, model)

        if not self.key_rotator:
            raise RuntimeError("Groq API keys not configured and MOCK_GROQ is false.")

        import aiohttp

        api_key = self.key_rotator.get_key()

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

        payload = {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": user_prompt}
            ],
            "temperature": temperature,
            "max_tokens": max_tokens
        }

        async with aiohttp.ClientSession() as session:
            async with session.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=aiohttp.ClientTimeout(total=60)
            ) as response:
                response.raise_for_status()
                result = await response.json()
                return result["choices"][0]["message"]["content"]

    def call_vision(self, system_prompt: str, image_data: str,
                    model: str = "llava-v1.5-7b-4096-preview") -> Dict[str, Any]:
        """Make a vision call to Groq API for image understanding."""
        # Check mock mode FIRST
        if self._use_mock():
            return self._mock_vision_call(system_prompt, image_data)

        if not self.key_rotator:
            raise RuntimeError("Groq API keys not configured and MOCK_GROQ is false.")

        import requests

        api_key = self.key_rotator.get_key()

        headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json"
        }

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

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=60
            )
            response.raise_for_status()
            result = response.json()
            text = result["choices"][0]["message"]["content"]

            # Try to parse as JSON if the model returned JSON
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
        except Exception as e:
            print(f"Groq vision call failed: {e}. Falling back to Tesseract.")
            return {
                "extracted_text": "",
                "confidence": 0.0,
                "language_detected": "en"
            }

    # ==================== Mock Responses ====================

    def _mock_call(self, system_prompt: str, user_prompt: str, model: str) -> str:
        """Return a mock response for testing."""
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
                        "confidence_scores": {"material_type": 0.95, "grade": 0.92, "quantity": 0.90}
                    }
                ],
                "language": "en",
                "is_sub_inquiry": False,
                "price_inclusive_gst": False,
                "overall_confidence": 0.92
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
            "language_detected": "mixed"
        }
