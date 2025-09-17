# app/services/serp_service.py

import os
import requests
import json
from dotenv import load_dotenv
from typing import Optional

load_dotenv()

SERPER_API_KEY = os.getenv("SERPER_API_KEY")

def get_serp_results(query: str, location: Optional[str] = None, num_results: int = 10) -> dict:
    """
    Gets the Search Engine Results Page (SERP) results for a given query.

    Args:
        query: The search query string.
        location: Optional location for the search.
        num_results: The number of results to fetch.

    Returns:
        A dictionary containing the SERP results.
    """
    if not SERPER_API_KEY:
        raise ValueError("SERPER_API_KEY not found in environment variables.")

    url = "https://google.serper.dev/search"
    payload = {
        "q": query,
        "num": num_results
    }
    
    if location:
        payload["location"] = location

    headers = {
        'X-API-KEY': SERPER_API_KEY,
        'Content-Type': 'application/json'
    }

    try:
        response = requests.post(url, headers=headers, data=json.dumps(payload))
        response.raise_for_status()
        return response.json()
    except requests.exceptions.RequestException as e:
        print(f"Error fetching SERP results: {e}")
        return {"error": str(e)}