import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
import time
import random
import pandas as pd
import logging
import os
import sys
from datetime import datetime

# ============ CONFIGURATION ============
BASE_URL1 = "https://www.99acres.com/new-projects-in-north-delhi-ffid"
BASE_URL="https://www.99acres.com/search/property/rent/residential/delhi?city=1075722&preference=P&area_unit=1&res_com=R?page=1"
TOTAL_PAGES = 1
OUTPUT_FOLDER = "data"
OUTPUT_FILE = "data.csv"
HEADLESS = False
MAX_RETRIES = 3
SCROLL_PAUSE_TIME = 3
PAGE_LOAD_TIMEOUT = 60
WAIT_AFTER_LOAD = 5

# ============ FIX WINDOWS CONSOLE ENCODING ============
if sys.platform == 'win32':
    sys.stdout.reconfigure(encoding='utf-8')
    sys.stderr.reconfigure(encoding='utf-8')

# ============ LOGGING SETUP ============
os.makedirs("logs", exist_ok=True)
log_filename = f"logs/scraper_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(levelname)s - %(message)s",
    handlers=[
        logging.FileHandler(log_filename, encoding='utf-8'),
        logging.StreamHandler(sys.stdout)
    ]
)

# ============ BUILD DRIVER ============
def build_driver(headless=False):
    """Initialize undetected Chrome driver with stealth settings."""
    try:
        options = uc.ChromeOptions()
        
        # Anti-detection settings
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-infobars")
        options.add_argument("--disable-extensions")
        options.add_argument("--disable-gpu")
        options.add_argument("--start-maximized")
        options.add_argument("--window-size=1920,1080")
        
        # Random user agent
        user_agents = [
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36"
        ]
        options.add_argument(f"user-agent={random.choice(user_agents)}")
        
        if headless:
            options.add_argument("--headless=new")
        
        logging.info(">>> Initializing Chrome driver...")
        driver = uc.Chrome(options=options, version_main=None)
        driver.set_page_load_timeout(PAGE_LOAD_TIMEOUT)
        
        logging.info(">>> Chrome driver initialized successfully")
        return driver
        
    except Exception as e:
        logging.error(f">>> Failed to initialize driver: {e}")
        raise

# ============ SCROLL PAGE ============
def scroll_page_gradually(driver):
    """Scroll page gradually to trigger lazy loading."""
    try:
        logging.info(">>> Scrolling page gradually...")
        
        # Get total height
        total_height = driver.execute_script("return document.body.scrollHeight")
        viewport_height = driver.execute_script("return window.innerHeight")
        
        current_position = 0
        scroll_step = 300
        
        while current_position < total_height:
            # Scroll down by step
            driver.execute_script(f"window.scrollTo(0, {current_position});")
            time.sleep(random.uniform(0.3, 0.6))
            
            current_position += scroll_step
            
            # Check if new content loaded
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height > total_height:
                total_height = new_height
        
        # Scroll back to top
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        
        logging.info(">>> Scrolling completed")
        
    except Exception as e:
        logging.warning(f"Error during scrolling: {e}")

# ============ EXTRACT PROJECT DATA ============
def extract_project_data(listing):
    """Extract data from a single listing element."""
    project = {
        "Project Name": "N/A",
        "Location": "N/A",
        "Price": "N/A",
        "Builder": "N/A",
        "Configuration": "N/A"
    }
    
    try:
        # Get all text from the listing
        listing_text = listing.text
        
        # Project Name - try multiple selectors
        selectors_name = [
            "h2",
            "[class*='projectName']",
            "a[class*='heading']",
            ".NpsrpTuple__npsrpHead"
        ]
        
        for selector in selectors_name:
            try:
                elem = listing.find_element(By.CSS_SELECTOR, selector)
                if elem and elem.text.strip():
                    project["Project Name"] = elem.text.strip()
                    break
            except:
                continue
        
        # Location
        selectors_location = [
            "[class*='subHeading']",
            "[class*='location']",
            "span[class*='locality']"
        ]
        
        for selector in selectors_location:
            try:
                elem = listing.find_element(By.CSS_SELECTOR, selector)
                if elem and elem.text.strip():
                    project["Location"] = elem.text.strip()
                    break
            except:
                continue
        
        # Price
        selectors_price = [
            "[class*='price']",
            "[class*='Price']",
            "td:nth-child(2)"
        ]
        
        for selector in selectors_price:
            try:
                elem = listing.find_element(By.CSS_SELECTOR, selector)
                text = elem.text.strip()
                if text and ('₹' in text or 'Lac' in text or 'Cr' in text):
                    project["Price"] = text
                    break
            except:
                continue
        
        # Builder
        selectors_builder = [
            "[class*='developer']",
            "[class*='builder']",
            "td:nth-child(1)"
        ]
        
        for selector in selectors_builder:
            try:
                elem = listing.find_element(By.CSS_SELECTOR, selector)
                if elem and elem.text.strip():
                    project["Builder"] = elem.text.strip()
                    break
            except:
                continue
        
        # Configuration
        selectors_config = [
            "[class*='config']",
            "[class*='bhk']",
            "td:nth-child(3)"
        ]
        
        for selector in selectors_config:
            try:
                elem = listing.find_element(By.CSS_SELECTOR, selector)
                text = elem.text.strip()
                if text and ('BHK' in text or 'Bedroom' in text):
                    project["Configuration"] = text
                    break
            except:
                continue
            
    except Exception as e:
        logging.warning(f"Error extracting project data: {e}")
    
    return project

# ============ SCRAPE SINGLE PAGE ============
def scrape_page(driver, page_number):
    """Scrape a single page of listings."""
    url = f"{BASE_URL}?page={page_number}"
    logging.info(f"\n{'='*70}")
    logging.info(f">>> Scraping page {page_number}: {url}")
    logging.info(f"{'='*70}")
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            # Navigate to page
            logging.info(f">>> Attempt {attempt}/{MAX_RETRIES} - Loading page...")
            driver.get(url)
            
            # Wait for page to load
            logging.info(f">>> Waiting {WAIT_AFTER_LOAD} seconds for page to load...")
            time.sleep(WAIT_AFTER_LOAD)
            
            # Scroll to trigger lazy loading
            scroll_page_gradually(driver)
            
            # Try multiple listing selectors
            logging.info(">>> Searching for listings...")
            
            listing_selectors = [
                ".NpsrpTuple__npsrpCard",
                "[class*='projectTuple']",
                "[class*='card']",
                "table tr"
            ]
            
            listings = []
            used_selector = None
            
            for selector in listing_selectors:
                try:
                    logging.info(f">>> Trying selector: {selector}")
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    if elements and len(elements) > 3:  # At least 3 listings
                        listings = elements
                        used_selector = selector
                        logging.info(f">>> SUCCESS! Found {len(listings)} elements with: {selector}")
                        break
                    else:
                        logging.info(f">>> Found only {len(elements)} elements, trying next selector...")
                        
                except Exception as e:
                    logging.warning(f">>> Selector {selector} failed: {e}")
                    continue
            
            if not listings:
                logging.warning(f">>> No listings found on page {page_number}")
                
                # Save debug info
                save_debug_info(driver, page_number, attempt)
                
                if attempt < MAX_RETRIES:
                    logging.info(f">>> Retrying in 10 seconds...")
                    time.sleep(10)
                    continue
                else:
                    logging.error(f">>> Failed after {MAX_RETRIES} attempts")
                    return []
            
            # Extract data from each listing
            projects = []
            logging.info(f">>> Extracting data from {len(listings)} listings...")
            
            for i, listing in enumerate(listings[:20], 1):  # Limit to first 20
                try:
                    project = extract_project_data(listing)
                    
                    # Only add if we got a project name
                    if project["Project Name"] != "N/A":
                        projects.append(project)
                        logging.info(f">>> [{i}] {project['Project Name']}")
                    
                except Exception as e:
                    logging.warning(f">>> Error extracting listing {i}: {e}")
            
            if projects:
                logging.info(f"\n>>> SUCCESS! Extracted {len(projects)} valid projects from page {page_number}")
                time.sleep(random.uniform(5, 8))
                return projects
            else:
                logging.warning(f">>> No valid projects extracted from page {page_number}")
                if attempt < MAX_RETRIES:
                    time.sleep(10)
                    continue
                    
        except Exception as e:
            logging.error(f">>> Error on page {page_number}, attempt {attempt}: {e}")
            save_debug_info(driver, page_number, attempt)
            
            if attempt < MAX_RETRIES:
                time.sleep(15)
    
    logging.error(f">>> Failed to scrape page {page_number} after {MAX_RETRIES} attempts")
    return []

# ============ SAVE DEBUG INFO ============
def save_debug_info(driver, page_number, attempt):
    """Save screenshot and HTML for debugging."""
    try:
        debug_folder = "debug_pages"
        os.makedirs(debug_folder, exist_ok=True)
        
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        
        # Screenshot
        screenshot_path = f"{debug_folder}/page{page_number}_attempt{attempt}_{timestamp}.png"
        driver.save_screenshot(screenshot_path)
        
        # HTML
        html_path = f"{debug_folder}/page{page_number}_attempt{attempt}_{timestamp}.html"
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(driver.page_source)
        
        logging.info(f">>> Debug files saved to {debug_folder}")
        
    except Exception as e:
        logging.warning(f"Could not save debug info: {e}")

# ============ SAVE TO CSV ============
def save_to_csv(projects, output_path):
    """Save projects to CSV file."""
    try:
        if not projects:
            logging.warning(">>> No data to save")
            return False
        
        df = pd.DataFrame(projects)
        
        # Remove duplicates
        initial_count = len(df)
        df = df.drop_duplicates(subset=['Project Name'], keep='first')
        removed = initial_count - len(df)
        
        if removed > 0:
            logging.info(f">>> Removed {removed} duplicate entries")
        
        # Save to CSV
        df.to_csv(output_path, index=False, encoding='utf-8-sig')
        logging.info(f"\n{'='*70}")
        logging.info(f">>> SUCCESS! Saved {len(df)} projects to: {output_path}")
        logging.info(f"{'='*70}")
        
        # Show preview
        logging.info("\n>>> PREVIEW OF DATA:")
        logging.info(df.head(10).to_string(index=False))
        
        return True
        
    except Exception as e:
        logging.error(f">>> Error saving to CSV: {e}")
        return False

# ============ MAIN FUNCTION ============
def main():
    """Main scraping function."""
    driver = None
    all_projects = []
    
    try:
        # Create output folder
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        output_path = os.path.join(OUTPUT_FOLDER, OUTPUT_FILE)
        
        logging.info("\n" + "="*70)
        logging.info(">>> STARTING WEB SCRAPER")
        logging.info("="*70)
        logging.info(f"Target: {BASE_URL}")
        logging.info(f"Pages to scrape: {TOTAL_PAGES}")
        logging.info(f"Output: {output_path}")
        logging.info("="*70 + "\n")
        
        # Initialize driver
        driver = build_driver(headless=HEADLESS)
        
        # Scrape each page
        for page in range(1, TOTAL_PAGES + 1):
            data = scrape_page(driver, page)
            
            if data:
                all_projects.extend(data)
                logging.info(f">>> Running total: {len(all_projects)} projects collected")
            else:
                logging.warning(f">>> No data from page {page}, continuing...")
            
            # Break if no data from first page
            if page == 1 and not data:
                logging.error(">>> Could not scrape first page! Check debug files.")
                logging.info(">>> TIP: The website might be blocking automated access.")
                logging.info(">>> TIP: Try running with HEADLESS=False and check the browser window.")
                break
        
        # Save results
        if all_projects:
            save_to_csv(all_projects, output_path)
        else:
            logging.error("\n>>> FAILED! No data scraped from any page!")
            logging.info(">>> Please check:")
            logging.info("    1. Internet connection")
            logging.info("    2. Website is accessible")
            logging.info("    3. Debug files in debug_pages/ folder")
            
    except KeyboardInterrupt:
        logging.warning("\n>>> Scraping interrupted by user")
        if all_projects:
            output_path = os.path.join(OUTPUT_FOLDER, OUTPUT_FILE)
            logging.info(">>> Saving collected data...")
            save_to_csv(all_projects, output_path)
            
    except Exception as e:
        logging.error(f">>> Critical error: {e}", exc_info=True)
        
    finally:
        if driver:
            try:
                logging.info("\n>>> Closing browser...")
                driver.quit()
                logging.info(">>> Browser closed")
            except Exception as e:
                logging.warning(f"Error closing driver: {e}")
        
        logging.info("\n" + "="*70)
        logging.info(">>> SCRAPING COMPLETED")
        logging.info("="*70 + "\n")

if __name__ == "__main__":
    main()