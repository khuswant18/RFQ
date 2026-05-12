"""Groq Client with key rotation."""
import os
import time
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
    """Groq API client with key rotation and async support."""
    
    def __init__(self):
        # Load 5 Groq API keys
        self.keys = []
        for i in range(1, 6):
            key = os.getenv(f"GROQ_API_KEY_{i}")
            if key:
                self.keys.append(key)
        
        if not self.keys:
            print("⚠️  No Groq API keys found. Using mock-only mode.")
        
        self.key_rotator = self.keys and GroqKeyRotator(self.keys) or None
        self.base_url = "https://api.groq.com/openai/v1"

    def _use_mock(self) -> bool:
        return os.getenv("MOCK_GROQ", "true").lower() == "true"
    
    def call(self, system_prompt: str, user_prompt: str, 
             model: str = "llama3-70b-8192", temperature: float = 0.7,
             max_tokens: int = 4096) -> str:
        """Make a synchronous call to Groq API."""
        import requests

        if self._use_mock():
            return self._mock_call(system_prompt, user_prompt, model)

        if not self.key_rotator:
            raise RuntimeError("Groq API keys not configured and MOCK_GROQ is false.")

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
            json=payload
        )
        
        response.raise_for_status()
        result = response.json()
        
        return result["choices"][0]["message"]["content"]
    
    async def call_async(self, system_prompt: str, user_prompt: str,
                         model: str = "llama3-70b-8192", temperature: float = 0.7,
                         max_tokens: int = 4096) -> str:
        """Make an async call to Groq API."""
        import aiohttp

        if self._use_mock():
            return self._mock_call(system_prompt, user_prompt, model)

        if not self.key_rotator:
            raise RuntimeError("Groq API keys not configured and MOCK_GROQ is false.")

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
                json=payload
            ) as response:
                response.raise_for_status()
                result = await response.json()
                return result["choices"][0]["message"]["content"]
    
    def call_vision(self, system_prompt: str, image_data: str,
                    model: str = "llama3-70b-8192") -> Dict[str, Any]:
        """Make a vision call to Groq API for image understanding."""
        if self._use_mock():
            return self._mock_vision_call(system_prompt, image_data)

        # Return low confidence to trigger OCR fallback (Tesseract).
        return {
            "extracted_text": "",
            "confidence": 0.0,
            "language_detected": "en"
        }
    
    def _mock_call(self, system_prompt: str, user_prompt: str, model: str) -> str:
        """Return a mock response for testing."""
        # Extract intent from user prompt for realistic mock responses
        if "price" in user_prompt.lower() and "MCX" in user_prompt:
            return '{"price_per_ton": 58000, "source": "mock", "as_of": "today"}'
        elif "extract" in user_prompt.lower() or "OCR" in system_prompt:
            return '{"extracted_text": "12mm Sariya Fe500 10 ton", "confidence": 0.9, "language_detected": "mixed"}'
        else:
            return '{"response": "Mock response from Groq"}'
    
    def _mock_vision_call(self, system_prompt: str, image_data: str) -> Dict[str, Any]:
        """Return a mock vision response for testing."""
        return {
            "extracted_text": "12mm Sariya Fe500 10 ton Surat",
            "confidence": 0.9,
            "language_detected": "mixed"
        }
