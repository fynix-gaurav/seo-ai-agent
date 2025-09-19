# # In backend/app/services/scraper_service.py

# import os
# import requests
# from bs4 import BeautifulSoup
# from dotenv import load_dotenv
# from tenacity import retry, stop_after_attempt, wait_exponential, RetryError

# load_dotenv()
# # --- Use your new Bright Data Proxy credentials ---
# BRIGHTDATA_USERNAME = os.getenv("BRIGHTDATA_USERNAME")
# BRIGHTDATA_PASSWORD = os.getenv("BRIGHTDATA_PASSWORD")
# BRIGHTDATA_HOST = "brd.superproxy.io"
# BRIGHTDATA_PORT = 33335

# def is_valid_scraping_url(url: str) -> bool:
#     """
#     Checks if a URL is a standard HTML page and not a direct link to a file or video platform.
#     """
#     if any(url.lower().endswith(ext) for ext in ['.pdf', '.jpg', '.png', '.zip', '.mp4']):
#         print(f"Skipping invalid file URL: {url}")
#         return False
#     if any(domain in url for domain in ['youtube.com', 'vimeo.com']):
#         print(f"Skipping video platform URL: {url}")
#         return False
#     return True

# @retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=2, max=10))
# def _make_brightdata_request_via_proxy(url: str) -> requests.Response:
#     """
#     Internal function that makes a single, robust request to a URL
#     via the Bright Data Web Unlocker proxy.
#     """
#     if not (BRIGHTDATA_USERNAME and BRIGHTDATA_PASSWORD):
#         raise ValueError("Bright Data credentials are not configured in .env file.")

#     proxy_url = (
#         f"http://{BRIGHTDATA_USERNAME}:{BRIGHTDATA_PASSWORD}@"
#         f"{BRIGHTDATA_HOST}:{BRIGHTDATA_PORT}"
#     )
    
#     proxies = {
#         "http": proxy_url,
#         "https": proxy_url,
#     }

#     print(f"Scraping {url} via Bright Data Web Unlocker...")
#     # The request is made directly to the target URL, but routed through the proxy
#     response = requests.get(url, proxies=proxies, timeout=180, verify=False)
#     response.raise_for_status()
#     return response

# def scrape_url_for_headings(url: str) -> list[str]:
#     """
#     Scrapes a single URL for its H2 and H3 headings using Bright Data's
#     Web Unlocker API with robust error handling.
#     """
#     if not is_valid_scraping_url(url):
#         return []

#     try:
#         response = _make_brightdata_request_via_proxy(url)
#         soup = BeautifulSoup(response.content, 'lxml')
#         headings = [h.get_text(strip=True) for h in soup.find_all(['h2', 'h3'])]
#         return headings

#     except RetryError as e:
#         print(f"Bright Data failed for URL {url} after multiple attempts. Last error: {e}")
#         return []
#     except (requests.exceptions.RequestException, ValueError) as e:
#         print(f"Bright Data request failed for URL {url} with a general error: {e}")
#         return []



# Revised version with dual-service approach (ScrapingAnt + Bright Data)
# 

import os
import requests
from bs4 import BeautifulSoup
from dotenv import load_dotenv
from tenacity import retry, stop_after_attempt, wait_exponential, RetryError

load_dotenv()
# --- Credentials for both services ---
SCRAPINGANT_API_KEY = os.getenv("SCRAPINGANT_API_KEY")
BRIGHTDATA_USERNAME = os.getenv("BRIGHTDATA_USERNAME")
BRIGHTDATA_PASSWORD = os.getenv("BRIGHTDATA_PASSWORD")
BRIGHTDATA_HOST = "brd.superproxy.io"
BRIGHTDATA_PORT = 33335

def is_valid_scraping_url(url: str) -> bool:
    """Checks if a URL is a standard HTML page and not a direct link to a file or video platform."""
    if any(url.lower().endswith(ext) for ext in ['.pdf', '.jpg', '.png', '.zip', '.mp4']):
        print(f"Skipping invalid file URL: {url}")
        return False
    if any(domain in url for domain in ['youtube.com', 'vimeo.com']):
        print(f"Skipping video platform URL: {url}")
        return False
    return True

@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=2, min=2, max=10))
def _make_scrapingant_request(url: str) -> requests.Response:
    """Internal function for the standard, free-tier request."""
    api_url = "https://api.scrapingant.com/v2/general"
    params = {'url': url, 'x-api-key': SCRAPINGANT_API_KEY, 'browser': 'true'}
    response = requests.get(api_url, params=params, timeout=180)
    response.raise_for_status()
    return response

@retry(stop=stop_after_attempt(2), wait=wait_exponential(multiplier=2, min=2, max=10))
def _make_brightdata_request_via_proxy(url: str) -> requests.Response:
    """Makes a premium request via the Bright Data Web Unlocker proxy."""
    if not (BRIGHTDATA_USERNAME and BRIGHTDATA_PASSWORD):
        raise ValueError("Bright Data credentials are not configured in .env file.")
    proxy_url = f"http://{BRIGHTDATA_USERNAME}:{BRIGHTDATA_PASSWORD}@{BRIGHTDATA_HOST}:{BRIGHTDATA_PORT}"
    proxies = {"http": proxy_url, "https": proxy_url}
    response = requests.get(url, proxies=proxies, timeout=180, verify=False)
    response.raise_for_status()
    return response

def scrape_url_for_headings(url: str) -> list[str]:
    """
    Intelligently scrapes a URL using a two-tiered, cost-saving approach.
    Tries the free service first, then escalates to Bright Data if blocked.
    """
    if not is_valid_scraping_url(url):
        return []

    try:
        # --- ATTEMPT 1: Use the standard, free scraper ---
        print(f"Attempting standard scrape for {url} with ScrapingAnt...")
        response = _make_scrapingant_request(url)
    except RetryError as e:
        if isinstance(e.last_attempt.exception(), requests.exceptions.HTTPError):
            print(f"Standard scrape blocked for {url}. Escalating to premium Bright Data...")

            # --- ATTEMPT 2: If blocked, use the premium service ---
            try:
                response = _make_brightdata_request_via_proxy(url)
            except (RetryError, requests.exceptions.RequestException, ValueError) as premium_e:
                print(f"Premium Bright Data also failed for {url}: {premium_e}")
                return []
        else:
            print(f"Standard scrape failed for {url} with a network error after retries: {e}")
            return []

    # --- If either attempt succeeds, parse the HTML ---
    try:
        soup = BeautifulSoup(response.content, 'lxml')
        return [h.get_text(strip=True) for h in soup.find_all(['h2', 'h3'])]
    except Exception as parse_e:
        print(f"Failed to parse HTML from {url}: {parse_e}")
        return []

