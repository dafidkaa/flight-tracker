import requests
from bs4 import BeautifulSoup
import json
import datetime
import re
import logging
import os
from typing import Dict, List, Optional, Any

# Create logs directory if it doesn't exist
os.makedirs('../logs', exist_ok=True)

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('../logs/scraper.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('zagreb_airport_scraper')

class ZagrebAirportScraper:
    """
    Scraper for Zagreb Airport flight information
    """
    
    def __init__(self):
        self.base_url = 'https://www.zagreb-airport.hr'
        self.arrivals_url = f'{self.base_url}/en/passengers/flight-information/arrivals/34'
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        }
    
    def _clean_text(self, text: str, prefix: str = '') -> str:
        """Clean text by removing prefix and extra whitespace"""
        if prefix:
            text = re.sub(f'^{prefix}\\s*', '', text, flags=re.IGNORECASE)
        return text.strip()
    
    def _make_absolute_url(self, url: str) -> str:
        """Convert relative URLs to absolute URLs"""
        if url and not url.startswith(('http://', 'https://')):
            return f"{self.base_url}{url if url.startswith('/') else '/' + url}"
        return url
    
    def scrape_arrivals(self) -> Optional[Dict[str, Any]]:
        """
        Scrape arrivals information from Zagreb Airport website
        
        Returns:
            Dictionary containing flight information or None if scraping failed
        """
        try:
            logger.info(f"Fetching arrivals data from {self.arrivals_url}")
            response = requests.get(self.arrivals_url, headers=self.headers)
            
            if response.status_code != 200:
                logger.error(f"Failed to fetch data: Status code {response.status_code}")
                return None
            
            soup = BeautifulSoup(response.text, 'html.parser')
            flight_table = soup.find('table', {'id': 'tablicaletenja'})
            
            if not flight_table:
                logger.error("Flight table not found")
                return None
            
            flights = []
            rows = flight_table.find_all('tr')
            
            # Skip the header row
            for row in rows[1:]:
                cells = row.find_all(['td', 'th'])
                
                # Skip rows that don't have enough cells
                if len(cells) < 8:
                    continue
                
                # Extract airline information
                airline_cell = cells[0]
                airline_logo = None
                airline_name = airline_cell.get_text(strip=True)
                
                img = airline_cell.find('img')
                if img and img.has_attr('src'):
                    airline_logo = self._make_absolute_url(img['src'])
                    if img.has_attr('alt'):
                        airline_name = img['alt']
                
                # Extract flight data with proper cleaning
                flight_data = {
                    "airline": {
                        "name": airline_name,
                        "logo": airline_logo
                    },
                    "scheduled_time": self._clean_text(cells[2].get_text(), "Scheduled"),
                    "expected_time": self._clean_text(cells[3].get_text(), "Expected"),
                    "origin": self._clean_text(cells[4].get_text()),
                    "flight_number": self._clean_text(cells[5].get_text(), "Flight No\\."),
                    "baggage": self._clean_text(cells[6].get_text(), "Baggage"),
                    "gate": self._clean_text(cells[7].get_text(), "Gate"),
                    "status": self._clean_text(cells[8].get_text(), "Status") if len(cells) > 8 else "Unknown"
                }
                
                flights.append(flight_data)
            
            # Create result object with metadata
            result = {
                "timestamp": datetime.datetime.now().isoformat(),
                "source": self.arrivals_url,
                "flights": flights
            }
            
            logger.info(f"Successfully scraped {len(flights)} flights")
            return result
            
        except Exception as e:
            logger.error(f"Error scraping arrivals: {str(e)}")
            return None
    
    def save_to_json(self, data: Dict[str, Any], filepath: str) -> bool:
        """
        Save flight data to JSON file
        
        Args:
            data: Flight data dictionary
            filepath: Path to save the JSON file
            
        Returns:
            True if successful, False otherwise
        """
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
            logger.info(f"Saved flight data to {filepath}")
            return True
        except Exception as e:
            logger.error(f"Error saving data to {filepath}: {str(e)}")
            return False

# Function to run the scraper
def scrape_and_save():
    """
    Run the scraper and save the results
    
    Returns:
        Flight data dictionary or None if scraping failed
    """
    scraper = ZagrebAirportScraper()
    flight_data = scraper.scrape_arrivals()
    
    if flight_data:
        scraper.save_to_json(flight_data, 'data/sample_data.json')
    
    return flight_data

if __name__ == "__main__":
    scrape_and_save()