"""
__all__ = ['WebSearchTool', 'search_web', 'search_documentation', 'search_code_examples']

Web Search Integration for FounderAI
Simple web search using DuckDuckGo (no API key required)
"""

import requests
import json
from typing import Dict, List, Optional, Any
from urllib.parse import quote

class WebSearchTool:
    def __init__(self):
        """Function __init__."""
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        })
    
    def search_web(self, query: str, max_results: int = 5) -> Dict[str, Any]:
        """
        Search the web using DuckDuckGo instant answers and results
        """
        try:
            # Try DuckDuckGo instant answers first
            instant_answer = self._get_duckduckgo_instant(query)
            if instant_answer:
                return {
                    "success": True,
                    "query": query,
                    "type": "instant_answer",
                    "answer": instant_answer,
                    "results": []
                }
            
            # Fall back to basic search results
            search_results = self._get_basic_search_results(query, max_results)
            
            return {
                "success": True,
                "query": query,
                "type": "search_results",
                "results": search_results
            }
            
        except Exception as e:
            return {
                "success": False,
                "error": f"Web search failed: {e}",
                "query": query
            }
    
    def _get_duckduckgo_instant(self, query: str) -> Optional[str]:
        """Get DuckDuckGo instant answer if available"""
        try:
            url = f"https://api.duckduckgo.com/?q={quote(query)}&format=json&no_html=1&skip_disambig=1"
            response = self.session.get(url, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            
            # Check for instant answer
            if data.get('Abstract'):
                return data['Abstract']
            elif data.get('Definition'):
                return data['Definition']
            elif data.get('Answer'):
                return data['Answer']
            
            return None
            
        except Exception:
            return None
    
    def _get_basic_search_results(self, query: str, max_results: int) -> List[Dict[str, str]]:
        """
        Get basic search results using a simple approach
        Note: This is a simplified implementation. For production use,
        consider using proper search APIs like Google Custom Search, Bing, etc.
        """
        try:
            # This is a placeholder implementation
            # In a real implementation, you'd use a proper search API
            results = [
                {
                    "title": f"Search result for: {query}",
                    "url": "https://example.com",
                    "snippet": f"This is a placeholder result for the query '{query}'. "
                             "To implement real search, use Google Custom Search API, "
                             "Bing Search API, or similar services."
                }
            ]
            
            return results[:max_results]
            
        except Exception as e:
            return [{"error": f"Search failed: {e}"}]
    
    def search_documentation(self, query: str, site: str = None) -> Dict[str, Any]:
        """
        Search for documentation on specific sites
        """
        if site:
            search_query = f"site:{site} {query}"
        else:
            search_query = f"{query} documentation"
        
        return self.search_web(search_query, max_results=3)
    
    def search_code_examples(self, query: str, language: str = None) -> Dict[str, Any]:
        """
        Search for code examples
        """
        if language:
            search_query = f"{query} {language} code example"
        else:
            search_query = f"{query} code example"
        
        return self.search_web(search_query, max_results=3)