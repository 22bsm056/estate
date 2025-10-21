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
BASE_URL = "https://www.99acres.com/search/property/rent/residential/delhi"
SEARCH_PARAMS = "?city=1075722&preference=P&area_unit=1&res_com=R"
TOTAL_PAGES = 1
OUTPUT_FOLDER = "data"
OUTPUT_FILE = "data.csv"
HEADLESS = False
MAX_RETRIES = 2
WAIT_AFTER_LOAD = 6

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
    """Initialize undetected Chrome driver."""
    try:
        options = uc.ChromeOptions()
        
        options.add_argument("--disable-blink-features=AutomationControlled")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--no-sandbox")
        options.add_argument("--start-maximized")
        options.add_argument("--window-size=1920,1080")
        
        user_agent = "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        options.add_argument(f"user-agent={user_agent}")
        
        if headless:
            options.add_argument("--headless=new")
        
        logging.info(">>> Initializing Chrome driver...")
        driver = uc.Chrome(options=options, version_main=None)
        driver.set_page_load_timeout(60)
        
        logging.info(">>> Chrome driver initialized successfully")
        return driver
        
    except Exception as e:
        logging.error(f">>> Failed to initialize driver: {e}")
        raise

# ============ SCROLL PAGE ============
def scroll_page_gradually(driver):
    """Scroll page to load all content."""
    try:
        logging.info(">>> Scrolling page...")
        
        last_height = driver.execute_script("return document.body.scrollHeight")
        
        for i in range(4):
            driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
            time.sleep(2)
            
            new_height = driver.execute_script("return document.body.scrollHeight")
            if new_height == last_height:
                break
            last_height = new_height
        
        driver.execute_script("window.scrollTo(0, 0);")
        time.sleep(1)
        
        logging.info(">>> Scrolling completed")
        
    except Exception as e:
        logging.warning(f"Error during scrolling: {e}")

# ============ EXTRACT PROPERTY DATA ============
def extract_property_data(listing):
    """Extract data from a single property listing based on actual HTML structure."""
    property_data = {
        "Property Title": "N/A",
        "Location": "N/A",
        "Price": "N/A",
        "Property Type": "N/A",
        "Area": "N/A",
        "Bedrooms": "N/A",
        "Furnishing": "N/A",
        "Posted By": "N/A",
        "Rating": "N/A"
    }
    
    try:
        # Property Title - from tupleNew__propertyHeading class
        try:
            title_elem = listing.find_element(By.CSS_SELECTOR, ".tupleNew__propertyHeading, a.tupleNew__propertyHeading")
            property_data["Property Title"] = title_elem.text.strip()
        except:
            try:
                title_elem = listing.find_element(By.CSS_SELECTOR, "h2")
                property_data["Property Title"] = title_elem.text.strip()
            except:
                pass
        
        # Location - from tupleNew__locationName
        try:
            location_elem = listing.find_element(By.CSS_SELECTOR, ".tupleNew__locationName")
            property_data["Location"] = location_elem.text.strip()
        except:
            pass
        
        # Rating - from tupleNew__locRatings span
        try:
            rating_elem = listing.find_element(By.CSS_SELECTOR, ".tupleNew__locRatings span")
            property_data["Rating"] = rating_elem.text.strip()
        except:
            pass
        
        # Furnishing Status - from tupleNew__furnished
        try:
            furnished_elem = listing.find_element(By.CSS_SELECTOR, ".tupleNew__furnished")
            property_data["Furnishing"] = furnished_elem.text.strip()
        except:
            pass
        
        # Property Type - from tupleNew__propType
        try:
            proptype_elem = listing.find_element(By.CSS_SELECTOR, ".tupleNew__propType")
            property_data["Property Type"] = proptype_elem.text.strip()
        except:
            pass
        
        # Price - from tupleNew__priceValWrap span (₹45,000)
        try:
            price_elem = listing.find_element(By.CSS_SELECTOR, ".tupleNew__priceValWrap span")
            property_data["Price"] = price_elem.text.strip()
        except:
            try:
                price_elem = listing.find_element(By.CSS_SELECTOR, ".tupleNew__priceValWrap")
                property_data["Price"] = price_elem.text.strip()
            except:
                pass
        
        # Bedrooms - from tupleNew__perSqftWrap (format: "/Bedroom")
        try:
            bedroom_elem = listing.find_element(By.CSS_SELECTOR, ".tupleNew__perSqftWrap")
            bedroom_text = bedroom_elem.text.strip()
            if "Bedroom" in bedroom_text:
                property_data["Bedrooms"] = bedroom_text
        except:
            pass
        
        # Area/Deposit - from tupleNew__perSqftWrap__ellipsis (₹1 Deposit ₹25,000)
        try:
            area_elem = listing.find_element(By.CSS_SELECTOR, ".tupleNew__perSqftWrap__ellipsis")
            area_text = area_elem.text.strip()
            if area_text:
                property_data["Area"] = area_text
        except:
            pass
        
        # If we didn't get a valid title, skip this listing
        if property_data["Property Title"] == "N/A" or len(property_data["Property Title"]) < 3:
            return None
            
    except Exception as e:
        logging.warning(f"Error extracting property data: {e}")
        return None
    
    return property_data

# ============ SCRAPE SINGLE PAGE ============
def scrape_page(driver, page_number):
    """Scrape a single page of listings."""
    if page_number == 1:
        url = BASE_URL + SEARCH_PARAMS
    else:
        url = f"{BASE_URL}{SEARCH_PARAMS}&page={page_number}"
    
    logging.info(f"\n{'='*70}")
    logging.info(f">>> Scraping page {page_number}: {url}")
    logging.info(f"{'='*70}")
    
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            logging.info(f">>> Attempt {attempt}/{MAX_RETRIES} - Loading page...")
            driver.get(url)
            
            logging.info(f">>> Waiting {WAIT_AFTER_LOAD} seconds for page to load...")
            time.sleep(WAIT_AFTER_LOAD)
            
            scroll_page_gradually(driver)
            
            logging.info(">>> Searching for property listings...")
            
            # Target the exact wrapper from the screenshot
            listing_selectors = [
                "div[class*='tupleNew__']",  # Main tuple wrapper
                ".tupleNew__locAndTags",     # Alternative
                "[id*='tuple']"              # Fallback
            ]
            
            listings = []
            used_selector = None
            
            for selector in listing_selectors:
                try:
                    logging.info(f">>> Trying selector: {selector}")
                    elements = driver.find_elements(By.CSS_SELECTOR, selector)
                    
                    # Filter to get only valid property cards
                    valid_elements = []
                    for elem in elements:
                        try:
                            # Check if it contains property-specific elements
                            if (elem.find_elements(By.CSS_SELECTOR, ".tupleNew__propertyHeading") or 
                                elem.find_elements(By.CSS_SELECTOR, ".tupleNew__priceValWrap")):
                                valid_elements.append(elem)
                        except:
                            continue
                    
                    if valid_elements and len(valid_elements) >= 5:
                        listings = valid_elements
                        used_selector = selector
                        logging.info(f">>> SUCCESS! Found {len(listings)} valid property listings with: {selector}")
                        break
                    else:
                        logging.info(f">>> Found only {len(valid_elements)} valid listings")
                        
                except Exception as e:
                    logging.warning(f">>> Selector failed: {e}")
                    continue
            
            if not listings:
                logging.warning(f">>> No listings found on page {page_number}")
                save_debug_info(driver, page_number, attempt)
                
                if attempt < MAX_RETRIES:
                    logging.info(f">>> Retrying in 10 seconds...")
                    time.sleep(10)
                    continue
                else:
                    return []
            
            # Extract data
            properties = []
            logging.info(f">>> Extracting data from {len(listings)} listings...")
            
            for i, listing in enumerate(listings[:30], 1):
                try:
                    prop = extract_property_data(listing)
                    
                    if prop and prop["Property Title"] != "N/A":
                        properties.append(prop)
                        # Show preview
                        title = prop['Property Title'][:50]
                        price = prop['Price']
                        location = prop['Location'][:30] if prop['Location'] != "N/A" else "N/A"
                        logging.info(f">>> [{i}] {title}... | {price} | {location}")
                    
                except Exception as e:
                    logging.warning(f">>> Error on listing {i}: {e}")
                    continue
            
            if properties:
                logging.info(f"\n>>> SUCCESS! Extracted {len(properties)} valid properties from page {page_number}")
                time.sleep(random.uniform(4, 7))
                return properties
            else:
                logging.warning(f">>> No valid properties extracted from page {page_number}")
                if attempt < MAX_RETRIES:
                    time.sleep(10)
                    continue
                    
        except Exception as e:
            logging.error(f">>> Error on page {page_number}: {e}")
            save_debug_info(driver, page_number, attempt)
            
            if attempt < MAX_RETRIES:
                time.sleep(15)
    
    logging.error(f">>> Failed to scrape page {page_number}")
    return []


# ============ SAVE TO CSV (APPEND MODE) ============
def save_to_csv(properties, output_path):
    """Save properties to CSV file with APPEND mode - NEVER DELETES OLD DATA."""
    try:
        if not properties:
            logging.warning(">>> No data to save")
            return False
        
        new_df = pd.DataFrame(properties)
        
        # Add timestamp to track when data was added
        new_df['Scraped_Date'] = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        
        # Check if file exists
        if os.path.exists(output_path):
            logging.info(f">>> File exists! Reading existing data...")
            
            try:
                # Read existing data with error handling
                existing_df = pd.read_csv(output_path, encoding='utf-8-sig')
                
                logging.info(f">>> Existing data: {len(existing_df)} rows")
                logging.info(f">>> New data: {len(new_df)} rows")
                
                # Combine old and new data - OLD DATA COMES FIRST
                combined_df = pd.concat([existing_df, new_df], ignore_index=True)
                
                logging.info(f">>> Combined total: {len(combined_df)} rows")
                
                # Remove duplicates based on Property Title and Location
                # keep='first' means we keep the OLDEST entry (from existing data)
                before_dedup = len(combined_df)
                combined_df = combined_df.drop_duplicates(
                    subset=['Property Title', 'Location'], 
                    keep='first'
                )
                after_dedup = len(combined_df)
                removed = before_dedup - after_dedup
                
                if removed > 0:
                    logging.info(f">>> Removed {removed} duplicate entries")
                
                # IMPORTANT: Save combined data back to file
                combined_df.to_csv(output_path, index=False, encoding='utf-8-sig')
                
                # Calculate new unique entries added
                new_unique = after_dedup - len(existing_df)
                
                logging.info(f"\n{'='*70}")
                logging.info(f">>> APPEND SUCCESS!")
                logging.info(f">>> Previous total: {len(existing_df)} properties")
                logging.info(f">>> New unique added: {new_unique} properties")
                logging.info(f">>> Current total: {len(combined_df)} properties")
                logging.info(f">>> File location: {output_path}")
                logging.info(f"{'='*70}")
                
            except Exception as e:
                logging.error(f">>> Error reading existing file: {e}")
                logging.info(">>> Creating backup and saving new data...")
                
                # Create backup of corrupted file
                backup_path = output_path.replace('.csv', f'_backup_{datetime.now().strftime("%Y%m%d_%H%M%S")}.csv')
                if os.path.exists(output_path):
                    os.rename(output_path, backup_path)
                    logging.info(f">>> Backup saved to: {backup_path}")
                
                # Save new data
                new_df.to_csv(output_path, index=False, encoding='utf-8-sig')
                logging.info(f">>> New file created with {len(new_df)} properties")
            
        else:
            logging.info(f">>> No existing file found. Creating new file...")
            
            # Remove duplicates in new data
            new_df = new_df.drop_duplicates(
                subset=['Property Title', 'Location'], 
                keep='first'
            )
            
            # Save new file
            new_df.to_csv(output_path, index=False, encoding='utf-8-sig')
            
            logging.info(f"\n{'='*70}")
            logging.info(f">>> NEW FILE CREATED!")
            logging.info(f">>> Total properties: {len(new_df)}")
            logging.info(f">>> File location: {output_path}")
            logging.info(f"{'='*70}")
        
        # Show preview of latest NEW data added
        logging.info("\n>>> PREVIEW OF NEW DATA ADDED:")
        print("\n" + new_df.head(10).to_string(index=False, max_colwidth=40))
        
        return True
        
    except Exception as e:
        logging.error(f">>> Error saving to CSV: {e}", exc_info=True)
        return False

# ============ MAIN FUNCTION ============
def main():
    """Main scraping function."""
    driver = None
    all_properties = []
    
    try:
        os.makedirs(OUTPUT_FOLDER, exist_ok=True)
        output_path = os.path.join(OUTPUT_FOLDER, OUTPUT_FILE)
        
        # Check existing data before starting
        existing_count = 0
        if os.path.exists(output_path):
            try:
                existing_df = pd.read_csv(output_path, encoding='utf-8-sig')
                existing_count = len(existing_df)
            except:
                existing_count = 0
        
        logging.info("\n" + "="*70)
        logging.info(">>> 99ACRES PROPERTY SCRAPER - APPEND MODE")
        logging.info("="*70)
        logging.info(f"Target: {BASE_URL}{SEARCH_PARAMS}")
        logging.info(f"Pages to scrape: {TOTAL_PAGES}")
        logging.info(f"Output file: {output_path}")
        logging.info(f"Mode: APPEND (data will be ADDED, not replaced)")
        if existing_count > 0:
            logging.info(f"Existing data found: {existing_count} properties")
        else:
            logging.info(f"No existing data - will create new file")
        logging.info("="*70 + "\n")
        
        driver = build_driver(headless=HEADLESS)
        
        for page in range(1, TOTAL_PAGES + 1):
            data = scrape_page(driver, page)
            
            if data:
                all_properties.extend(data)
                logging.info(f">>> Running total: {len(all_properties)} properties collected")
            else:
                logging.warning(f">>> No data from page {page}")
            
            if page == 1 and not data:
                logging.error(">>> Could not scrape first page! Check debug files.")
                break
        
        if all_properties:
            save_to_csv(all_properties, output_path)
            
            # Verify final count
            try:
                final_df = pd.read_csv(output_path, encoding='utf-8-sig')
                logging.info(f"\n>>> VERIFICATION: Final file contains {len(final_df)} total properties")
            except:
                pass
        else:
            logging.error("\n>>> FAILED! No property data scraped!")
            logging.info(">>> Check debug_pages/ folder for screenshots and HTML")
            
    except KeyboardInterrupt:
        logging.warning("\n>>> Interrupted by user")
        if all_properties:
            save_to_csv(all_properties, os.path.join(OUTPUT_FOLDER, OUTPUT_FILE))
            
    except Exception as e:
        logging.error(f">>> Critical error: {e}", exc_info=True)
        
    finally:
        if driver:
            try:
                logging.info("\n>>> Closing browser...")
                driver.quit()
                logging.info(">>> Browser closed")
            except:
                pass
        
        logging.info("\n" + "="*70)
        logging.info(">>> SCRAPING COMPLETED")
        logging.info("="*70 + "\n")

if __name__ == "__main__":
    main()