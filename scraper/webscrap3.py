"""
99Acres Property Scraper - WORKING VERSION
Correctly identifies property URLs with the actual URL pattern
"""

import sys
import os
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from bs4 import BeautifulSoup
import pandas as pd
import time
import random
import logging
import re
from datetime import datetime

# ============ LOGGING SETUP ============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PropertyScraper99Acres:
    """Scraper that correctly extracts 99acres property URLs and details"""
    
    def __init__(self, headless=False):
        self.driver = None
        self.headless = headless
        self.properties = []
        self.base_url = "https://www.99acres.com"
    
    def init_driver(self):
        """Initialize Selenium Chrome driver"""
        try:
            logger.info("Initializing Chrome driver...")
            
            options = webdriver.ChromeOptions()
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--no-sandbox')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-gpu')
            
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
            options.add_argument(f'user-agent={user_agent}')
            
            if self.headless:
                options.add_argument('--headless=new')
            
            service = Service(ChromeDriverManager().install())
            self.driver = webdriver.Chrome(service=service, options=options)
            self.driver.set_page_load_timeout(60)
            
            logger.info("✓ Chrome driver initialized")
            return True
            
        except Exception as e:
            logger.error(f"✗ Failed to initialize driver: {e}")
            return False
    
    def close_driver(self):
        """Close browser safely"""
        if self.driver:
            try:
                self.driver.quit()
                logger.info("✓ Browser closed")
            except:
                pass
    
    def extract_urls_from_page(self, page_num, property_type="rent", city="delhi"):
        """Extract property URLs from listing page"""
        
        if page_num == 1:
            url = f"{self.base_url}/search/property/{property_type}/{city}?city=1075722&preference=R&area_unit=1&res_com=R&isPreLeased=N"
        else:
            url = f"{self.base_url}/search/property/{property_type}/{city}?city=1075722&preference=R&area_unit=1&res_com=R&isPreLeased=N&page={page_num}"
        
        logger.info(f"\n{'='*70}")
        logger.info(f"Page {page_num}")
        logger.info(f"URL: {url}")
        logger.info(f"{'='*70}")
        
        try:
            self.driver.get(url)
            logger.info("Waiting 6 seconds for page to render...")
            time.sleep(6)
            
            # Scroll to load lazy-loaded content
            logger.info("Scrolling page...")
            for i in range(10):
                self.driver.execute_script("window.scrollBy(0, 400);")
                time.sleep(0.5)
            
            page_source = self.driver.page_source
            
            # Save debug HTML
            debug_file = f"debug_page_{page_num}.html"
            with open(debug_file, 'w', encoding='utf-8') as f:
                f.write(page_source)
            
            soup = BeautifulSoup(page_source, 'html.parser')
            
            # Find all links
            all_links = soup.find_all('a', href=True)
            logger.info(f"Found {len(all_links)} total links")
            
            property_urls = []
            
            # Property URLs have pattern: /3-bhk-bedroom-.../r2-spid-W80509401
            # They contain property type (bedroom, independent, etc.) and end with spid-
            for link in all_links:
                href = link.get('href', '')
                
                if not href:
                    continue
                
                # The URL pattern is: /{description}-r{id}-spid-{code}
                # Key indicators: contains "bhk" or "bedroom" or "independent" and contains "spid"
                if ('bhk' in href.lower() or 'bedroom' in href.lower() or 
                    'independent' in href.lower() or 'flat' in href.lower() or
                    'apartment' in href.lower()) and 'spid-' in href.lower():
                    
                    # Make sure it's a full URL
                    if not href.startswith('http'):
                        href = self.base_url + href if href.startswith('/') else self.base_url + '/' + href
                    
                    # Skip if it's a search page
                    if '/search/' not in href:
                        if href not in property_urls:
                            property_urls.append(href)
            
            # Remove duplicates
            property_urls = list(dict.fromkeys(property_urls))
            
            logger.info(f"✓ Extracted {len(property_urls)} property URLs")
            if property_urls:
                logger.info(f"  Sample: {property_urls[0][:100]}")
            
            return property_urls
            
        except Exception as e:
            logger.error(f"✗ Error on page {page_num}: {e}")
            return []
    
    def extract_property_details(self, property_url):
        """Extract details from individual property page"""
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
        
        try:
            logger.info(f"  Fetching: {property_url[:80]}...")
            self.driver.get(property_url)
            time.sleep(3)
            
            # Scroll to load all content
            for i in range(5):
                self.driver.execute_script("window.scrollBy(0, 400);")
                time.sleep(0.5)
            
            page_source = self.driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            all_text = soup.get_text()
            
            # ========== EXTRACT TITLE ==========
            title_tag = soup.find('h1')
            if title_tag:
                property_data["Property_Title"] = title_tag.get_text(strip=True)
            
            # ========== EXTRACT PRICE ==========
            # Look for ₹ symbol
            price_match = re.search(r'₹\s*([\d,.\s]+)(?:/month|per month|/yr|annual|Month)?', all_text)
            if price_match:
                price_text = price_match.group(0).strip()
                property_data["Price"] = price_text
            
            # ========== EXTRACT BEDROOMS, BATHROOMS, BALCONIES ==========
            bed_match = re.search(r'(\d+)\s*(?:BHK|Bedroom|bed)', all_text, re.IGNORECASE)
            if bed_match:
                property_data["Bedrooms"] = bed_match.group(1)
            
            bath_match = re.search(r'(\d+)\s*(?:Bathroom|bath)', all_text, re.IGNORECASE)
            if bath_match:
                property_data["Bathrooms"] = bath_match.group(1)
            
            balcony_match = re.search(r'(\d+)\s*(?:Balcon)', all_text, re.IGNORECASE)
            if balcony_match:
                property_data["Balconies"] = balcony_match.group(1)
            
            # ========== EXTRACT CARPET AREA ==========
            area_match = re.search(r'([\d,]+)\s*(?:sq\.?\s*ft|sqft|Carpet Area)', all_text, re.IGNORECASE)
            if area_match:
                property_data["Carpet_Area"] = area_match.group(1) + " sq.ft"
            
            # ========== EXTRACT RATE PER SQ FT ==========
            rate_match = re.search(r'₹\s*([\d,]+)\s*(?:per|/)\s*sq\.?\s*ft', all_text, re.IGNORECASE)
            if rate_match:
                property_data["Rate_per_sqft"] = "₹" + rate_match.group(1)
            
            # ========== EXTRACT DEPOSIT ==========
            deposit_match = re.search(r'(?:Deposit|Advance)[:\s]*(₹[\d,\s]+)', all_text, re.IGNORECASE)
            if deposit_match:
                property_data["Deposit"] = deposit_match.group(1).replace('\n', ' ')
            
            # ========== EXTRACT FURNISHING ==========
            if 'Semi-Furnished' in all_text:
                property_data["Furnishing"] = "Semi-Furnished"
            elif 'Furnished' in all_text and 'Unfurnished' not in all_text:
                property_data["Furnishing"] = "Furnished"
            elif 'Unfurnished' in all_text:
                property_data["Furnishing"] = "Unfurnished"
            
            # ========== EXTRACT LOCATION ==========
            # Look for location in common places (Delhi location names)
            location_keywords = ['Paschim Vihar', 'West Delhi', 'Delhi', 'Nagar', 'Sector', 'Phase']
            for keyword in location_keywords:
                if keyword.lower() in all_text.lower():
                    location_match = re.search(rf'{keyword}[^\n]*', all_text, re.IGNORECASE)
                    if location_match:
                        property_data["Location"] = location_match.group(0).strip()[:80]
                        break
            
            # ========== EXTRACT ADDRESS ==========
            # Address usually contains RWA, Block, Society, etc.
            address_patterns = re.findall(r'(?:RWA|Block|Sector|Flat|House|Society|Building|Phase)[^\n]{5,100}', all_text)
            if address_patterns:
                property_data["Address"] = address_patterns[0].strip()[:100]
            
            # ========== EXTRACT POSTED BY AND DATE ==========
            if 'Dealer' in all_text:
                property_data["Posted_By"] = "Dealer"
            elif 'Owner' in all_text:
                property_data["Posted_By"] = "Owner"
            
            # Look for posted date
            date_match = re.search(r'(?:Posted|Listed)\s*(?:on)?\s*(\d{1,2}\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)[^\n]{0,20})', all_text, re.IGNORECASE)
            if date_match:
                property_data["Posted_Date"] = date_match.group(1).strip()
            
            # ========== EXTRACT AVAILABLE FROM ==========
            if 'Immediate' in all_text or 'immediate' in all_text:
                property_data["Available_From"] = "Immediate"
            else:
                available_match = re.search(r'Available\s*(?:from)?[:\s]*(\d{1,2}\s*(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec))', all_text, re.IGNORECASE)
                if available_match:
                    property_data["Available_From"] = available_match.group(1).strip()
            
            # ========== EXTRACT PROPERTY TYPE ==========
            if 'Independent' in all_text:
                property_data["Property_Type"] = "Independent"
            elif 'Apartment' in all_text or 'Flat' in all_text:
                property_data["Property_Type"] = "Apartment/Flat"
            elif 'Villa' in all_text:
                property_data["Property_Type"] = "Villa"
            
            logger.info(f"    ✓ {property_data['Property_Title'][:60]}")
            return property_data
            
        except Exception as e:
            logger.warning(f"    ✗ Error: {str(e)[:50]}")
            return None
    
    def scrape_all(self, property_type="rent", city="delhi", num_pages=2):
        """Main scraping function"""
        if not self.init_driver():
            return False
        
        try:
            logger.info(f"\n{'#'*70}")
            logger.info(f"99ACRES PROPERTY SCRAPER")
            logger.info(f"Type: {property_type} | City: {city} | Pages: {num_pages}")
            logger.info(f"{'#'*70}\n")
            
            all_urls = []
            
            # Step 1: Collect property URLs
            logger.info("STEP 1: Collecting property URLs from listing pages...\n")
            for page in range(20, num_pages + 1):
                urls = self.extract_urls_from_page(page, property_type, city)
                all_urls.extend(urls)
                
                if page < num_pages:
                    time.sleep(random.uniform(2, 4))
            
            if not all_urls:
                logger.error("\n✗ No property URLs found!")
                return False
            
            logger.info(f"\n{'='*70}")
            logger.info(f"✓ Total URLs collected: {len(all_urls)}")
            logger.info(f"{'='*70}\n")
            
            # Step 2: Extract details from each property
            logger.info("STEP 2: Extracting details from each property...\n")
            
            for idx, url in enumerate(all_urls, 1):
                logger.info(f"[{idx}/{len(all_urls)}]")
                prop_data = self.extract_property_details(url)
                
                if prop_data:
                    self.properties.append(prop_data)
                
                time.sleep(random.uniform(1, 2))
            
            # Step 3: Save to CSV
            if self.properties:
                self.save_to_csv()
                return True
            else:
                logger.error("No properties extracted")
                return False
                
        except Exception as e:
            logger.error(f"Critical error: {e}")
            return False
        finally:
            self.close_driver()
    
    def save_to_csv(self):
        """Save properties to CSV file"""
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
            df.to_csv(filename, index=False, encoding='utf-8')
            
            logger.info(f"\n{'='*70}")
            logger.info(f"✓ SUCCESS!")
            logger.info(f"File saved: {filename}")
            logger.info(f"Total properties: {len(df)}")
            logger.info(f"{'='*70}\n")
            
        except Exception as e:
            logger.error(f"Error saving CSV: {e}")


if __name__ == "__main__":
    # Install: pip install selenium webdriver-manager beautifulsoup4 pandas
    
    scraper = PropertyScraper99Acres(headless=False)
    scraper.scrape_all(
        property_type="rent",
        city="delhi",
        num_pages=35
    )