#!/usr/bin/env python3
"""
Melbourne Housing Data Scraper
Scrapes housing data from realestate.com.au for three suburbs:
- Highton, VIC 3216
- Ballarat Greater Region, VIC
- Werribee, VIC 3030
"""

from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.action_chains import ActionChains
from selenium.webdriver.common.keys import Keys
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
import json
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class HousingScraper:
    def __init__(self):
        self.driver = None
        self.data = []

        # Suburb URLs
        self.suburb_urls = {
            "Highton": "https://www.realestate.com.au/sold/in-highton,+vic+3216/list-",
            "Ballarat": "https://www.realestate.com.au/sold/in-ballarat+-+greater+region,+vic/list-",
            "Werribee": "https://www.realestate.com.au/sold/in-werribee,+vic+3030/list-",
        }

    def setup_chrome_driver(self):
        """Setup Chrome driver"""
        chrome_options = Options()
        # chrome_options.add_argument("--headless")  # Comment out to see browser
        # chrome_options.add_argument("--no-sandbox")
        # chrome_options.add_argument("--disable-dev-shm-usage")
        # chrome_options.add_argument("--disable-gpu")
        chrome_options.add_argument("--window-size=1920,1080")
        chrome_options.add_argument("--disable-blink-features=AutomationControlled")
        chrome_options.add_experimental_option("excludeSwitches", ["enable-automation"])
        chrome_options.add_experimental_option("useAutomationExtension", False)

        print("Setting up Chrome WebDriver...")
        self.driver = webdriver.Chrome(options=chrome_options)
        self.driver.execute_script(
            "Object.defineProperty(navigator, 'webdriver', {get: () => undefined})"
        )
        self.driver.set_page_load_timeout(30)
        print("✓ Chrome WebDriver initialized")

    def load_cookies_from_file(self, filename="www.realestate.com.au.cookies.json"):
        """Load cookies from JSON file"""
        try:
            with open(filename, "r") as f:
                cookies = json.load(f)
            print(f"✓ Loaded {len(cookies)} cookies from {filename}")
            return cookies
        except FileNotFoundError:
            print(f"✗ Cookie file {filename} not found!")
            return []
        except json.JSONDecodeError:
            print(f"✗ Error parsing {filename}!")
            return []

    def apply_cookies(self):
        """Apply cookies to the browser session"""
        # First navigate to the domain
        self.driver.get("https://www.realestate.com.au")
        time.sleep(15)

        cookies = self.load_cookies_from_file()
        for cookie in cookies:
            try:
                self.driver.add_cookie(cookie)
            except Exception as e:
                logger.warning(
                    f"Could not add cookie {cookie.get('name', 'unknown')}: {e}"
                )

        print(f"✓ Applied cookies to browser session")
        self.driver.get("https://www.realestate.com.au")
        time.sleep(15)

    def extract_price(self, price_text):
        """Extract numeric price from price text"""
        if not price_text:
            return None

        # Remove common price prefixes and clean
        price_text = price_text.replace("$", "").replace(",", "").strip()

        # Handle ranges (take the higher value)
        if "-" in price_text:
            prices = re.findall(r"\d+", price_text)
            if prices:
                return int(prices[-1])

        # Extract first number found
        numbers = re.findall(r"\d+", price_text)
        if numbers:
            return int(numbers[0])

        return None

    def extract_features(self, property_element):
        """Extract features from a property listing element"""
        try:
            # Initialize property data
            property_data = {
                "suburb": "",
                "address": "",
                "property_type": "",
                "bedrooms": None,
                "bathrooms": None,
                "parking": None,
                "land_size": "",
                "sold_price": None,
                "sold_date": "",
                "listing_url": "",
            }

            # Extract address # has class residential-card__details-link
            address_elem = property_element.select_one(
                "a.residential-card__details-link"
            )

            if address_elem:
                property_data["listing_url"] = (
                    "https://www.realestate.com.au" + address_elem.get("href", "")
                )

            address_elem = property_element.select_one(
                "a.residential-card__details-link span"
            )

            if address_elem:
                property_data["address"] = address_elem.text.split()

            if property_data["address"]:
                addrsss_parts = property_data["address"].split(",")
                # 401 Drummond Street South, Ballarat Central
                # after split we get ['401 Drummond Street South', 'Ballarat Central']
                # we want to get the last part
                property_data["suburb"] = addrsss_parts[-1].strip()

            # Extract property type
            # first select ".residential-card__primary p"
            type_elem = property_element.select_one(".residential-card__primary p")
            if type_elem:
                property_data["property_type"] = type_elem.text.strip()

            # Extract bedrooms, bathrooms, parking, land size
            features_ul = property_element.find(
                "ul", class_="residential-card__primary"
            )
            if features_ul:
                # Find all list items with aria-label
                feature_items = features_ul.find_all("li", {"aria-label": True})

                for item in feature_items:
                    aria_label = item.get("aria-label", "").lower()

                    # Extract the number from the p tag
                    p_tag = item.find("p")
                    if p_tag:
                        text = p_tag.text.strip()

                        if "bedroom" in aria_label:
                            beds = re.findall(r"\d+", text)
                            if beds:
                                property_data["bedrooms"] = int(beds[0])
                        elif "bathroom" in aria_label:
                            baths = re.findall(r"\d+", text)
                            if baths:
                                property_data["bathrooms"] = int(baths[0])
                        elif "car" in aria_label or "parking" in aria_label:
                            cars = re.findall(r"\d+", text)
                            if cars:
                                property_data["parking"] = int(cars[0])
                        elif "land size" in aria_label or "m²" in text:
                            property_data["land_size"] = text

            # Extract sold price
            price_elem = property_element.find("span", class_="property-price")
            if price_elem:
                property_data["sold_price"] = self.extract_price(price_elem.text)

            # Extract sold date
            date_elem = property_element.find("span", {"data-testid": "sold-date"})
            if date_elem:
                property_data["sold_date"] = date_elem.text.strip()

            return property_data

        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            return None

    def scrape_page(self, url, suburb_name):
        """Scrape a single page of listings"""
        try:
            logger.info(f"Scraping: {url}")
            self.driver.get(url)

            # Wait for page to load
            time.sleep(3)

            # Wait for listings to be present
            try:
                WebDriverWait(self.driver, 10).until(
                    EC.presence_of_element_located(
                        (By.CSS_SELECTOR, 'article[data-testid="ResidentialCard"]')
                    )
                )
            except:
                logger.warning(f"No listings found on page: {url}")
                return []

            # Get page source and parse with BeautifulSoup
            soup = BeautifulSoup(self.driver.page_source, "html.parser")

            # Find property listings
            listings = soup.find_all("article", {"data-testid": "ResidentialCard"})

            page_data = []
            for listing in listings:
                property_data = self.extract_features(listing)
                if property_data:
                    property_data["suburb"] = suburb_name
                    page_data.append(property_data)

            logger.info(f"Found {len(page_data)} properties on this page")
            return page_data

        except Exception as e:
            logger.error(f"Error scraping page {url}: {e}")
            return []

    def scrape_suburb(self, suburb_name, target_count=50):
        """Scrape properties for a specific suburb"""
        logger.info(f"Starting to scrape {suburb_name}")
        base_url = self.suburb_urls[suburb_name]

        page = 1
        suburb_data = []

        while len(suburb_data) < target_count and page <= 1:  # Limit to 10 pages
            url = f"{base_url}{page}"
            page_data = self.scrape_page(url, suburb_name)

            if not page_data:
                logger.info(f"No more data found for {suburb_name} at page {page}")
                break

            suburb_data.extend(page_data)
            logger.info(
                f"{suburb_name}: {len(suburb_data)} properties collected so far"
            )

            page += 1
            time.sleep(5)  # Be respectful with requests

        logger.info(f"Completed scraping {suburb_name}: {len(suburb_data)} properties")
        return suburb_data[:target_count]  # Return up to target_count

    def scrape_all_suburbs(self):
        """Scrape all three suburbs"""
        logger.info("Starting data collection for all suburbs")

        # Setup browser and cookies
        self.setup_chrome_driver()
        self.apply_cookies()

        try:
            for suburb_name in self.suburb_urls.keys():
                suburb_data = self.scrape_suburb(suburb_name, target_count=50)
                self.data.extend(suburb_data)
                logger.info(f"Total properties collected: {len(self.data)}")
                time.sleep(10)  # Pause between suburbs

            logger.info(
                f"Data collection completed. Total properties: {len(self.data)}"
            )

        finally:
            # Always close the browser
            if self.driver:
                self.driver.quit()
                print("✓ Browser closed")

    def save_to_csv(self, filename="melbourne_housing_data.csv"):
        """Save collected data to CSV file"""
        if not self.data:
            logger.warning("No data to save")
            return

        df = pd.DataFrame(self.data)

        # Clean and organize columns
        columns_order = [
            "suburb",
            "address",
            "property_type",
            "bedrooms",
            "bathrooms",
            "parking",
            "land_size",
            "sold_price",
            "sold_date",
            "listing_url",
        ]

        df = df.reindex(columns=columns_order)
        df.to_csv(filename, index=False)

        logger.info(f"Data saved to {filename}")
        logger.info(f"Dataset shape: {df.shape}")

        # Print summary statistics
        print("\n=== DATA COLLECTION SUMMARY ===")
        print(f"Total properties collected: {len(df)}")
        print(f"Properties per suburb:")
        print(df["suburb"].value_counts())
        print(f"\nProperty types:")
        print(df["property_type"].value_counts())
        print(f"\nPrice statistics:")
        print(df["sold_price"].describe())


def main():
    """Main function to run the scraper"""
    scraper = HousingScraper()

    try:
        scraper.scrape_all_suburbs()
        scraper.save_to_csv()

    except KeyboardInterrupt:
        logger.info("Scraping interrupted by user")
        if scraper.data:
            scraper.save_to_csv("partial_melbourne_housing_data.csv")
    except Exception as e:
        logger.error(f"Unexpected error: {e}")
        if scraper.data:
            scraper.save_to_csv("error_melbourne_housing_data.csv")
    finally:
        # Ensure browser is closed
        if scraper.driver:
            scraper.driver.quit()


if __name__ == "__main__":
    main()
