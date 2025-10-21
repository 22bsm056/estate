"""
99Acres Property Scraper - OPTIMIZED VERSION (10X FASTER)
Uses concurrent processing and optimized waits for maximum speed
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
from concurrent.futures import ThreadPoolExecutor, as_completed
from queue import Queue
import threading

# ============ LOGGING SETUP ============
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class PropertyScraper99Acres:
    """Optimized scraper with concurrent processing"""
    
    def __init__(self, headless=True, max_workers=2):
        self.headless = headless
        self.max_workers = max_workers  # Number of parallel browsers
        self.properties = []
        self.properties_lock = threading.Lock()
        self.base_url = "https://www.99acres.com"
        self.driver_pool = Queue()
    
    def create_driver(self):
        """Create a single driver instance"""
        try:
            options = webdriver.ChromeOptions()
            options.add_argument('--disable-blink-features=AutomationControlled')
            options.add_argument('--disable-dev-shm-usage')
            options.add_argument('--no-sandbox')
            options.add_argument('--window-size=1920,1080')
            options.add_argument('--disable-gpu')
            options.add_argument('--disable-images')  # Speed boost
            options.add_argument('--disable-extensions')
            options.add_argument('--disable-logging')
            options.add_argument('--disable-web-security')
            options.add_argument('--disk-cache-size=0')
            
            # Disable image loading for speed
            prefs = {
                "profile.managed_default_content_settings.images": 2,
                "profile.default_content_setting_values.notifications": 2,
            }
            options.add_experimental_option("prefs", prefs)
            
            user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
            options.add_argument(f'user-agent={user_agent}')
            
            if self.headless:
                options.add_argument('--headless=new')
            
            service = Service(ChromeDriverManager().install())
            driver = webdriver.Chrome(service=service, options=options)
            driver.set_page_load_timeout(30)
            
            return driver
            
        except Exception as e:
            logger.error(f"Failed to create driver: {e}")
            return None
    
    def get_driver(self):
        """Get a driver from pool or create new one"""
        if not self.driver_pool.empty():
            return self.driver_pool.get()
        return self.create_driver()
    
    def return_driver(self, driver):
        """Return driver to pool"""
        if driver:
            self.driver_pool.put(driver)
    
    def close_all_drivers(self):
        """Close all drivers in pool"""
        while not self.driver_pool.empty():
            driver = self.driver_pool.get()
            try:
                driver.quit()
            except:
                pass
    
    def extract_urls_from_page(self, page_num, property_type="rent", city="delhi"):
        """Extract property URLs from listing page - OPTIMIZED"""
        
        driver = self.get_driver()
        if not driver:
            return []
        
        try:
            if page_num == 1:
                url = f"{self.base_url}/search/property/{property_type}/{city}?city=1075722&preference=R&area_unit=1&res_com=R&isPreLeased=N"
            else:
                url = f"{self.base_url}/search/property/{property_type}/{city}?city=1075722&preference=R&area_unit=1&res_com=R&isPreLeased=N&page={page_num}"
            
            logger.info(f"Page {page_num} - Extracting URLs...")
            
            driver.get(url)
            
            # OPTIMIZED: Wait for specific element instead of fixed sleep
            try:
                WebDriverWait(driver, 10).until(
                    EC.presence_of_element_located((By.TAG_NAME, "a"))
                )
            except:
                pass
            
            # OPTIMIZED: Quick scroll - reduced from 10 iterations to 3
            for i in range(3):
                driver.execute_script("window.scrollBy(0, 800);")
                time.sleep(0.3)  # Reduced from 0.5
            
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            
            all_links = soup.find_all('a', href=True)
            property_urls = []
            
            for link in all_links:
                href = link.get('href', '')
                
                if not href:
                    continue
                
                if ('bhk' in href.lower() or 'bedroom' in href.lower() or 
                    'independent' in href.lower() or 'flat' in href.lower() or
                    'apartment' in href.lower()) and 'spid-' in href.lower():
                    
                    if not href.startswith('http'):
                        href = self.base_url + href if href.startswith('/') else self.base_url + '/' + href
                    
                    if '/search/' not in href and href not in property_urls:
                        property_urls.append(href)
            
            property_urls = list(dict.fromkeys(property_urls))
            logger.info(f"Page {page_num} - Found {len(property_urls)} URLs")
            
            return property_urls
            
        except Exception as e:
            logger.error(f"Error on page {page_num}: {e}")
            return []
        finally:
            self.return_driver(driver)
    
    def extract_property_details(self, property_url):
        """Extract details from property page - OPTIMIZED"""
        
        driver = self.get_driver()
        if not driver:
            return None
        
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
            driver.get(property_url)
            
            # OPTIMIZED: Wait for h1 instead of fixed sleep
            try:
                WebDriverWait(driver, 8).until(
                    EC.presence_of_element_located((By.TAG_NAME, "h1"))
                )
            except:
                time.sleep(1)
            
            # OPTIMIZED: Reduced scroll iterations from 5 to 2
            for i in range(2):
                driver.execute_script("window.scrollBy(0, 600);")
                time.sleep(0.2)  # Reduced from 0.5
            
            page_source = driver.page_source
            soup = BeautifulSoup(page_source, 'html.parser')
            all_text = soup.get_text()
            
            # ========== EXTRACT TITLE ==========
            title_tag = soup.find('h1')
            if title_tag:
                property_data["Property_Title"] = title_tag.get_text(strip=True)
            
            # ========== EXTRACT PRICE ==========
            price_match = re.search(r'₹\s*([\d,.\s]+)(?:/month|per month|/yr|annual|Month)?', all_text)
            if price_match:
                property_data["Price"] = price_match.group(0).strip()
            
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
            location_keywords = ['Paschim Vihar', 'West Delhi', 'Delhi', 'Nagar', 'Sector', 'Phase']
            for keyword in location_keywords:
                if keyword.lower() in all_text.lower():
                    location_match = re.search(rf'{keyword}[^\n]*', all_text, re.IGNORECASE)
                    if location_match:
                        property_data["Location"] = location_match.group(0).strip()[:80]
                        break
            
            # ========== EXTRACT ADDRESS ==========
            address_patterns = re.findall(r'(?:RWA|Block|Sector|Flat|House|Society|Building|Phase)[^\n]{5,100}', all_text)
            if address_patterns:
                property_data["Address"] = address_patterns[0].strip()[:100]
            
            # ========== EXTRACT POSTED BY AND DATE ==========
            if 'Dealer' in all_text:
                property_data["Posted_By"] = "Dealer"
            elif 'Owner' in all_text:
                property_data["Posted_By"] = "Owner"
            
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
            
            return property_data
            
        except Exception as e:
            logger.warning(f"Error extracting {property_url[:50]}: {str(e)[:50]}")
            return None
        finally:
            self.return_driver(driver)
    
    def scrape_all(self, property_type="rent", city="delhi", num_pages=35):
        """Main scraping function - OPTIMIZED with parallel processing"""
        
        logger.info(f"\n{'#'*70}")
        logger.info(f"99ACRES PROPERTY SCRAPER - OPTIMIZED VERSION")
        logger.info(f"Type: {property_type} | City: {city} | Pages: {num_pages}")
        logger.info(f"Workers: {self.max_workers}")
        logger.info(f"{'#'*70}\n")
        
        try:
            # Initialize driver pool
            logger.info(f"Initializing {self.max_workers} browser instances...")
            for _ in range(self.max_workers):
                driver = self.create_driver()
                if driver:
                    self.driver_pool.put(driver)
            
            logger.info(f"✓ {self.driver_pool.qsize()} browsers ready\n")
            
            # STEP 1: Collect URLs in parallel
            logger.info("STEP 1: Collecting URLs from all pages (parallel)...\n")
            all_urls = []
            
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_page = {
                    executor.submit(self.extract_urls_from_page, page, property_type, city): page 
                    for page in range(36, num_pages + 1)
                }
                
                for future in as_completed(future_to_page):
                    page = future_to_page[future]
                    try:
                        urls = future.result()
                        all_urls.extend(urls)
                    except Exception as e:
                        logger.error(f"Page {page} failed: {e}")
            
            # Remove duplicates
            all_urls = list(dict.fromkeys(all_urls))
            
            if not all_urls:
                logger.error("\n✗ No property URLs found!")
                return False
            
            logger.info(f"\n{'='*70}")
            logger.info(f"✓ Total unique URLs: {len(all_urls)}")
            logger.info(f"{'='*70}\n")
            
            # STEP 2: Extract details in parallel
            logger.info("STEP 2: Extracting property details (parallel)...\n")
            
            completed = 0
            with ThreadPoolExecutor(max_workers=self.max_workers) as executor:
                future_to_url = {
                    executor.submit(self.extract_property_details, url): url 
                    for url in all_urls
                }
                
                for future in as_completed(future_to_url):
                    url = future_to_url[future]
                    try:
                        prop_data = future.result()
                        if prop_data:
                            with self.properties_lock:
                                self.properties.append(prop_data)
                                completed += 1
                                if completed % 10 == 0:
                                    logger.info(f"Progress: {completed}/{len(all_urls)} properties extracted")
                    except Exception as e:
                        logger.error(f"Failed to extract {url[:50]}: {e}")
            
            logger.info(f"\n✓ Extraction complete: {len(self.properties)} properties")
            
            # STEP 3: Save to CSV
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
            self.close_all_drivers()
    
    def save_to_csv(self):
        """Save properties to CSV file"""
        try:
            df = pd.DataFrame(self.properties)
            
            columns = [
                "Property_Title", "Location", "Address", "Price",
                "Rate_per_sqft", "Deposit", "Property_Type", "Room_Type",
                "Bedrooms", "Bathrooms", "Balconies", "Furnishing", "Carpet_Area",
                "Available_From", "Available_For", "Posted_By", "Posted_Date",
                "Rating", "Nearby_Places", "Scraped_Date", "Property_URL"
            ]
            
            for col in columns:
                if col not in df.columns:
                    df[col] = "N/A"
            
            df = df[columns]
            
            filename = f"dataset_optimized_{datetime.now().strftime('%Y%m%d_%H%M%S')}.csv"
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
    
    # OPTIMIZED: Use 5 parallel browsers (adjust based on your system)
    scraper = PropertyScraper99Acres(headless=True, max_workers=5)
    
    scraper.scrape_all(
        property_type="rent",
        city="delhi",
        num_pages=55
    )