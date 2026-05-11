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
            # Return mock results for testing
            return self._mock_search(query)
        
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
    
    def _mock_search(self, query: str) -> List[Dict[str, Any]]:
        """Return mock search results for testing."""
        return [
            {
                "title": "MCX Steel Price Today",
                "link": "https://example.com/steel-price",
                "snippet": "Current MCX steel price: ₹58,000 per ton for Fe500 TMT bars."
            },
            {
                "title": "Steel Price Update",
                "link": "https://example.com/update",
                "snippet": "Steel prices have risen by 2% this week. Current rate: ₹58,500/ton."
            }
        ]
