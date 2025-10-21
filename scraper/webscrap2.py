"""
99Acres Property Scraper - Stealth / Retry version
Fixes HTTP 417 by removing the Expect header and adding CDP headers / UA overrides.
Features:
 - Random user-agents rotation
 - CDP extra HTTP headers and UA override
 - JS stealth injection (navigator.webdriver removal, permissions)
 - Optional proxy support
 - Polite delays, retries, and debug dumps
"""

import time
import random
import re
import logging
from datetime import datetime
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd

# ---------- CONFIG ----------
HEADLESS = False
NUM_PAGES = 30
PROPERTY_TYPE = "rent"
CITY = "delhi"
USE_PROXY = False                 # set True if you want to use proxy
PROXY = "http://username:password@host:port"  # example
RETRY_ATTEMPTS = 3
PAGE_LOAD_TIMEOUT = 60
# ----------------------------

logging.basicConfig(level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s")
logger = logging.getLogger(__name__)

USER_AGENTS = [
    # A few modern UAs to rotate
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64; rv:120.0) Gecko/20100101 Firefox/120.0",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 13_5) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/16.6 Safari/605.1.15",
]

STEALTH_JS = r"""
// Remove webdriver flag
Object.defineProperty(navigator, 'webdriver', {get: () => undefined});
// Mock plugins
Object.defineProperty(navigator, 'plugins', {get: () => [1,2,3,4,5]});
// Mock languages
Object.defineProperty(navigator, 'languages', {get: () => ['en-US','en']});
// Mock chrome object
window.chrome = { runtime: {} };
"""

class PropertyScraper99Acres:
    def __init__(self, headless=HEADLESS, use_proxy=USE_PROXY, proxy=PROXY):
        self.headless = headless
        self.use_proxy = use_proxy
        self.proxy = proxy
        self.driver = None
        self.properties = []
        self.base_url = "https://www.99acres.com"

    def init_driver(self):
        """Initialize Chrome with options, CDP headers, UA override, and JS stealth injection."""
        try:
            logger.info("Initializing Chrome driver...")
            options = webdriver.ChromeOptions()

            # Basic stealthy flags
            options.add_argument("--disable-blink-features=AutomationControlled")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1920,1080")
            options.add_argument("--disable-extensions")
            options.add_argument("--disable-infobars")
            options.add_argument("--disable-features=VizDisplayCompositor,NetworkService,NetworkServiceInProcess")
            options.add_experimental_option("excludeSwitches", ["enable-automation"])
            options.add_experimental_option("useAutomationExtension", False)

            if self.headless:
                # modern headless flag (newer Chrome)
                options.add_argument("--headless=new")

            # Proxy (optional)
            if self.use_proxy and self.proxy:
                options.add_argument(f"--proxy-server={self.proxy}")

            # pick a random UA for each session
            ua = random.choice(USER_AGENTS)
            options.add_argument(f"user-agent={ua}")

            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)

            # CDP: set UA override and extra headers (including clearing Expect)
            try:
                # Network must be enabled before setExtraHTTPHeaders
                self.driver.execute_cdp_cmd("Network.enable", {})
                # Set the same user agent via CDP (helps some servers)
                self.driver.execute_cdp_cmd("Network.setUserAgentOverride", {"userAgent": ua})
                # Set extra headers; ensure Expect header is blank/omitted
                extra_headers = {
                    "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8",
                    "Accept-Language": "en-US,en;q=0.9",
                    "Connection": "keep-alive",
                    "Referer": "https://www.google.com/",
                    "Upgrade-Insecure-Requests": "1",
                    # "Expect" omitted or set to empty string to avoid 417
                    "Expect": ""
                }
                self.driver.execute_cdp_cmd("Network.setExtraHTTPHeaders", {"headers": extra_headers})
            except Exception as e:
                logger.warning("CDP header setup failed (non-fatal): %s", e)

            # Inject stealth JS so it's applied on every navigation BEFORE scripts run
            try:
                self.driver.execute_cdp_cmd("Page.addScriptToEvaluateOnNewDocument", {"source": STEALTH_JS})
            except Exception as e:
                logger.warning("Stealth JS injection failed (non-fatal): %s", e)

            logger.info("✓ Chrome driver initialized (UA: %s)", ua)
            return True
        except Exception as e:
            logger.error("✗ Failed to initialize driver: %s", e)
            return False

    def close_driver(self):
        if self.driver:
            try:
                self.driver.quit()
                logger.info("✓ Browser closed")
            except:
                pass

    def _get_page_source_with_retries(self, url, retries=RETRY_ATTEMPTS):
        """Load a URL with retries, random delays, and debug dumps."""
        for attempt in range(1, retries + 1):
            try:
                logger.info("Loading: %s (attempt %d/%d)", url, attempt, retries)
                self.driver.get(url)
                # small randomized wait to let JS lazy-load content
                time.sleep(random.uniform(4.0, 7.0))
                # gentle scroll to trigger lazy-loaded content
                for _ in range(6):
                    self.driver.execute_script("window.scrollBy(0, 400);")
                    time.sleep(random.uniform(0.2, 0.6))
                page_source = self.driver.page_source

                # Save debug file for first attempt only (useful to inspect 417 pages)
                debug_file = f"debug_{re.sub(r'[^0-9a-zA-Z]', '_', url)[:60]}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
                with open(debug_file, "w", encoding="utf-8") as f:
                    f.write(page_source)
                logger.info("Saved debug HTML: %s", debug_file)
                return page_source

            except Exception as e:
                logger.warning("Load attempt %d failed: %s", attempt, str(e)[:200])
                # If last attempt, re-raise
                if attempt == retries:
                    logger.error("All retries failed for URL: %s", url)
                    return None
                # backoff before retry
                time.sleep(2 ** attempt + random.uniform(0.5, 1.5))
        return None

    def extract_urls_from_page(self, page_num, property_type="rent", city="delhi"):
        """Extract property URLs from a listing page"""
        if page_num == 1:
            url = f"{self.base_url}/search/property/{property_type}/{city}?city=1075722&preference=R&area_unit=1&res_com=R&isPreLeased=N"
        else:
            url = f"{self.base_url}/search/property/{property_type}/{city}?city=1075722&preference=R&area_unit=1&res_com=R&isPreLeased=N&page={page_num}"

        logger.info("\n" + "=" * 70)
        logger.info("Page %d -> %s", page_num, url)
        logger.info("=" * 70)
        page_src = self._get_page_source_with_retries(url)
        if not page_src:
            return []

        soup = BeautifulSoup(page_src, "html.parser")
        all_links = soup.find_all("a", href=True)
        logger.info("Found %d total links", len(all_links))

        property_urls = []
        for link in all_links:
            href = link.get("href", "")
            if not href:
                continue
            # heuristics: contain bhk/bedroom/flat/apartment/independent and spid- pattern
            lower = href.lower()
            if ("bhk" in lower or "bedroom" in lower or "flat" in lower or "apartment" in lower or "independent" in lower) and "spid-" in lower:
                if not href.startswith("http"):
                    href = self.base_url + href if href.startswith("/") else f"{self.base_url}/{href}"
                if "/search/" not in href:
                    property_urls.append(href)
        # dedupe preserving order
        property_urls = list(dict.fromkeys(property_urls))
        logger.info("✓ Extracted %d property URLs", len(property_urls))
        if property_urls:
            logger.info("  Sample: %s", property_urls[0][:120])
        return property_urls

    def extract_property_details(self, property_url):
        """Extract details from an individual property page"""
        property_data = {
            "Property_Title": "N/A",
            "Property_URL": property_url,
            "Location": "N/A",
            "Address": "N/A",
            "Price": "N/A",
            "Rate_per_sqft": "N/A",
            "Deposit": "N/A",
            "Property_Type": "N/A",
            "Room_Type": "N/A",
            "Bedrooms": "N/A",
            "Bathrooms": "N/A",
            "Balconies": "N/A",
            "Furnishing": "N/A",
            "Carpet_Area": "N/A",
            "Available_From": "N/A",
            "Available_For": "N/A",
            "Posted_By": "N/A",
            "Posted_Date": "N/A",
            "Rating": "N/A",
            "Nearby_Places": "N/A",
            "Scraped_Date": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }

        page_src = self._get_page_source_with_retries(property_url)
        if not page_src:
            return None

        try:
            soup = BeautifulSoup(page_src, "html.parser")
            all_text = soup.get_text(separator="\n")

            title_tag = soup.find("h1")
            if title_tag:
                property_data["Property_Title"] = title_tag.get_text(strip=True)

            # PRICE
            price_match = re.search(r'₹\s*([\d,.\s]+)(?:/month|per month|/yr|annual|Month)?', all_text)
            if price_match:
                property_data["Price"] = price_match.group(0).strip()

            # BEDROOMS, BATHROOMS, BALCONIES
            bed_match = re.search(r'(\d+)\s*(?:BHK|Bedroom|bed)', all_text, re.IGNORECASE)
            if bed_match:
                property_data["Bedrooms"] = bed_match.group(1)

            bath_match = re.search(r'(\d+)\s*(?:Bathroom|bath)', all_text, re.IGNORECASE)
            if bath_match:
                property_data["Bathrooms"] = bath_match.group(1)

            balcony_match = re.search(r'(\d+)\s*(?:Balcon)', all_text, re.IGNORECASE)
            if balcony_match:
                property_data["Balconies"] = balcony_match.group(1)

            # CARPET AREA
            area_match = re.search(r'([\d,]+)\s*(?:sq\.?\s*ft|sqft|Carpet Area)', all_text, re.IGNORECASE)
            if area_match:
                property_data["Carpet_Area"] = area_match.group(1) + " sq.ft"

            # RATE PER SQFT
            rate_match = re.search(r'₹\s*([\d,]+)\s*(?:per|/)\s*sq\.?\s*ft', all_text, re.IGNORECASE)
            if rate_match:
                property_data["Rate_per_sqft"] = "₹" + rate_match.group(1)

            # DEPOSIT
            deposit_match = re.search(r'(?:Deposit|Advance)[:\s]*(₹[\d,\s]+)', all_text, re.IGNORECASE)
            if deposit_match:
                property_data["Deposit"] = deposit_match.group(1).replace('\n', ' ')

            # FURNISHING
            if 'Semi-Furnished' in all_text:
                property_data["Furnishing"] = "Semi-Furnished"
            elif 'Furnished' in all_text and 'Unfurnished' not in all_text:
                property_data["Furnishing"] = "Furnished"
            elif 'Unfurnished' in all_text:
                property_data["Furnishing"] = "Unfurnished"

            # LOCATION
            location_keywords = ['Paschim Vihar', 'West Delhi', 'Delhi', 'Nagar', 'Sector', 'Phase']
            for keyword in location_keywords:
                if keyword.lower() in all_text.lower():
                    location_match = re.search(rf'{keyword}[^\n]*', all_text, re.IGNORECASE)
                    if location_match:
                        property_data["Location"] = location_match.group(0).strip()[:80]
                        break

            # ADDRESS
            address_patterns = re.findall(r'(?:RWA|Block|Sector|Flat|House|Society|Building|Phase)[^\n]{5,100}', all_text)
            if address_patterns:
                property_data["Address"] = address_patterns[0].strip()[:100]

            # POSTED BY and DATE
            if 'Dealer' in all_text:
                property_data["Posted_By"] = "Dealer"
            elif 'Owner' in all_text:
                property_data["Posted_By"] = "Owner"

            date_match = re.search(r'(?:Posted|Listed)\s*(?:on)?\s*(\d{1,2}\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[^\n]{0,20})', all_text, re.IGNORECASE)
            if date_match:
                property_data["Posted_Date"] = date_match.group(1).strip()

            if 'Immediate' in all_text or 'immediate' in all_text:
                property_data["Available_From"] = "Immediate"
            else:
                available_match = re.search(r'Available\s*(?:from)?[:\s]*(\d{1,2}\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec))', all_text, re.IGNORECASE)
                if available_match:
                    property_data["Available_From"] = available_match.group(1).strip()

            if 'Independent' in all_text:
                property_data["Property_Type"] = "Independent"
            elif 'Apartment' in all_text or 'Flat' in all_text:
                property_data["Property_Type"] = "Apartment/Flat"
            elif 'Villa' in all_text:
                property_data["Property_Type"] = "Villa"

            logger.info("    ✓ %s", property_data["Property_Title"][:60])
            return property_data

        except Exception as e:
            logger.warning("    ✗ Error parsing property: %s", str(e)[:150])
            return None

    def save_to_csv(self):
        try:
            df = pd.DataFrame(self.properties)
            columns = [
                "Property_Title", "Location", "Address", "Price",
                "Rate_per_sqft", "Deposit", "Property_Type", "Room_Type",
                "Bedrooms", "Bathrooms", "Balconies", "Furnishing", "Carpet_Area",
                "Available_From", "Available_For", "Posted_By", "Posted_Date",
                "Rating", "Nearby_Places", "Scraped_Date"
            ]
            for col in columns:
                if col not in df.columns:
                    df[col] = "N/A"
            df = df[columns]
            filename = f"dataset_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
            df.to_csv(filename, index=False, encoding="utf-8")
            logger.info("\n" + "=" * 70)
            logger.info("✓ SUCCESS! File saved: %s (Total properties: %d)", filename, len(df))
            logger.info("=" * 70 + "\n")
        except Exception as e:
            logger.error("Error saving CSV: %s", e)

    def scrape_all(self, property_type=PROPERTY_TYPE, city=CITY, num_pages=NUM_PAGES):
        if not self.init_driver():
            return False
        try:
            logger.info("\n" + "#" * 70)
            logger.info("99ACRES PROPERTY SCRAPER")
            logger.info("Type: %s | City: %s | Pages: %d", property_type, city, num_pages)
            logger.info("#" * 70 + "\n")

            all_urls = []
            # Step 1: collect URLs
            for page in range(20, num_pages + 1):
                urls = self.extract_urls_from_page(page, property_type, city)
                all_urls.extend(urls)
                # polite pause between listing pages
                time.sleep(random.uniform(2.0, 4.0))

            all_urls = list(dict.fromkeys(all_urls))
            if not all_urls:
                logger.error("✗ No property URLs found!")
                return False

            logger.info("\n" + "=" * 70)
            logger.info("✓ Total URLs collected: %d", len(all_urls))
            logger.info("=" * 70 + "\n")

            # Step 2: extract details
            for idx, url in enumerate(all_urls, 1):
                logger.info("[%d/%d] %s", idx, len(all_urls), url)
                prop = self.extract_property_details(url)
                if prop:
                    self.properties.append(prop)
                # random sleep to reduce pattern detection
                time.sleep(random.uniform(1.0, 2.5))

            # Step 3: save
            if self.properties:
                self.save_to_csv()
                return True
            else:
                logger.error("No properties extracted")
                return False

        except Exception as e:
            logger.error("Critical error: %s", e)
            return False
        finally:
            self.close_driver()


if __name__ == "__main__":
    scraper = PropertyScraper99Acres(headless=HEADLESS, use_proxy=USE_PROXY, proxy=PROXY)
    success = scraper.scrape_all(property_type=PROPERTY_TYPE, city=CITY, num_pages=NUM_PAGES)
    if success:
        logger.info("Scrape completed successfully")
    else:
        logger.error("Scrape failed")
