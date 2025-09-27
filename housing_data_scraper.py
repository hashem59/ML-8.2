#!/usr/bin/env python3
"""
Melbourne Housing Data Scraper
Scrapes housing data from realestate.com.au for three suburbs:
- Highton, VIC 3216
- Ballarat Greater Region, VIC
- Werribee, VIC 3030
"""

import requests
from bs4 import BeautifulSoup
import pandas as pd
import time
import re
from datetime import datetime
import logging

# Setup logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger(__name__)


class HousingScraper:
    def __init__(self):
        self.session = requests.Session()
        self.session.headers.update(
            {
                "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
            }
        )
        self.data = []

        # Suburb URLs
        self.suburb_urls = {
            "Highton": "https://www.realestate.com.au/sold/in-highton,+vic+3216/list-",
            "Ballarat": "https://www.realestate.com.au/sold/in-ballarat+-+greater+region,+vic/list-",
            "Werribee": "https://www.realestate.com.au/sold/in-werribee,+vic+3030/list-",
        }

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

            # Extract bedrooms, bathrooms, parking
            features_elem = property_element.find(
                "div", {"data-testid": "property-features"}
            )
            if features_elem:
                feature_spans = features_elem.find_all("span")
                for span in feature_spans:
                    text = span.text.strip()
                    if "bed" in text.lower():
                        beds = re.findall(r"\d+", text)
                        if beds:
                            property_data["bedrooms"] = int(beds[0])
                    elif "bath" in text.lower():
                        baths = re.findall(r"\d+", text)
                        if baths:
                            property_data["bathrooms"] = int(baths[0])
                    elif "car" in text.lower() or "parking" in text.lower():
                        cars = re.findall(r"\d+", text)
                        if cars:
                            property_data["parking"] = int(cars[0])

            # Extract sold price
            price_elem = property_element.find(
                "span", {"data-testid": "property-price"}
            )
            if price_elem:
                property_data["sold_price"] = self.extract_price(price_elem.text)

            # Extract sold date
            date_elem = property_element.find("span", {"data-testid": "sold-date"})
            if date_elem:
                property_data["sold_date"] = date_elem.text.strip()

            # Extract land size if available
            land_elem = property_element.find(
                "span", string=re.compile(r"m²|sqm", re.I)
            )
            if land_elem:
                property_data["land_size"] = land_elem.text.strip()

            return property_data

        except Exception as e:
            logger.error(f"Error extracting features: {e}")
            return None

    def scrape_page(self, url, suburb_name):
        """Scrape a single page of listings"""
        try:
            logger.info(f"Scraping: {url}")
            response = self.session.get(url, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, "html.parser")

            # Find property listings
            listings = soup.find_all("div", {"data-testid": "ResidentialCard"})

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
            time.sleep(2)  # Be respectful with requests

        logger.info(f"Completed scraping {suburb_name}: {len(suburb_data)} properties")
        return suburb_data[:target_count]  # Return up to target_count

    def scrape_all_suburbs(self):
        """Scrape all three suburbs"""
        logger.info("Starting data collection for all suburbs")

        for suburb_name in self.suburb_urls.keys():
            suburb_data = self.scrape_suburb(suburb_name, target_count=50)
            self.data.extend(suburb_data)
            logger.info(f"Total properties collected: {len(self.data)}")
            time.sleep(3)  # Pause between suburbs

        logger.info(f"Data collection completed. Total properties: {len(self.data)}")

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


if __name__ == "__main__":
    main()
