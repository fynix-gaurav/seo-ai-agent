# In backend/app/services/scraper_service.py

import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv

load_dotenv()
SCRAPINGANT_API_KEY = os.getenv("SCRAPINGANT_API_KEY")

def scrape_url_for_headings(url: str) -> list[str]:
    """
    Scrapes a single URL specifically for its H2 and H3 headings using ScrapingAnt.
    """
    if not SCRAPINGANT_API_KEY:
        print("ERROR: SCRAPINGANT_API_KEY is not configured in .env file.")
        return []

    print(f"Scraping headings from {url} via ScrapingAnt...")
    api_url = "https://api.scrapingant.com/v2/general"
    params = {'url': url, 'x-api-key': SCRAPINGANT_API_KEY, 'browser': 'false'}
    
    try:
        response = requests.get(api_url, params=params, timeout=60)
        response.raise_for_status()
        soup = BeautifulSoup(response.content, 'lxml')
        
        # Extract the text from all H2 and H3 tags
        headings = [h.get_text(strip=True) for h in soup.find_all(['h2', 'h3'])]
        return headings

    except requests.exceptions.RequestException as e:
        print(f"ScrapingAnt failed for URL {url}: {e}")
        return []