# backend/app/services/scraper_service.py
import requests
from bs4 import BeautifulSoup
from typing import List, Dict, Any
import logging

# Set up logging
logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger(__name__)

# It's crucial to mimic a real browser to avoid being blocked.
HEADERS = {
    'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
}

def scrape_url_content(url: str) -> Dict[str, Any]:
    """
    Scrapes a single URL for its H2s, H3s, and keywords (from body text).
    Includes a browser-like User-Agent to improve reliability.
    """
    try:
        response = requests.get(url, headers=HEADERS, timeout=10)
        response.raise_for_status()  # Will raise an HTTPError for bad responses (4xx or 5xx)
        
        soup = BeautifulSoup(response.content, 'html.parser')
        
        # Extract H2s and H3s
        h2s = [h2.get_text(strip=True) for h2 in soup.find_all('h2')]
        h3s = [h3.get_text(strip=True) for h3 in soup.find_all('h3')]
        
        # For simplicity, we'll treat body text as a source of keywords for now.
        # In a more advanced version, we could use NLP to extract key terms.
        if soup.body:
            body_text = soup.body.get_text(strip=True, separator=' ')
        else:
            body_text = ""

        return {
            "url": url,
            "h2s": h2s,
            "h3s": h3s,
            "text": body_text[:5000] # Limit text to avoid excessive data processing
        }

    except requests.exceptions.RequestException as e:
        logger.warning(f"Error scraping URL {url}: {e}")
        return None

def scrape_urls(urls: List[str]) -> Dict[str, Any]:
    """
    Scrapes a list of URLs and aggregates their content.
    """
    all_headings = []
    all_keywords = [] # This will be an aggregation of text

    for url in urls:
        logger.warning(f"Scraping content from: {url}")
        content = scrape_url_content(url)
        if content:
            all_headings.extend(content["h2s"])
            all_headings.extend(content["h3s"])
            all_keywords.append(content["text"])
    
    # Combine all scraped text into a single string for the AI to analyze
    full_text_corpus = " ".join(all_keywords)

    return {
        "headings": all_headings,
        "corpus": full_text_corpus
    }
