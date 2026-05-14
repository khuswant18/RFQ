"""Serper client for web search."""
import os
import json
from typing import List, Dict, Any

import requests


class SerperClient:
    """Client for Serper API (web search)."""

    def __init__(self, api_key: str = None):
        self.api_key = api_key or os.getenv("SERPER_API_KEY")
        self.base_url = "https://google.serper.dev/search"

    def search(self, query: str, num: int = 5) -> List[Dict[str, Any]]:
        """Search the web using Serper API."""
        if not self.api_key:
            raise RuntimeError("SERPER_API_KEY not configured.")

        headers = {
            "X-API-KEY": self.api_key,
            "Content-Type": "application/json"
        }

        payload = {
            "q": query,
            "num": num
        }

        response = requests.post(
            self.base_url,
            headers=headers,
            json=payload
        )

        response.raise_for_status()
        result = response.json()

        return result.get("organic", [])

