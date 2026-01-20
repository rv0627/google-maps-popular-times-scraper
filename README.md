# Google Maps Popular Times Scraper

A Python tool that uses Selenium to scrape "Popular Times" and live occupancy data from Google Maps locations. The data is exported to both JSON and Excel formats.

## Features
- **Popular Times Extraction**: Scrapes percentage occupancy for each hour of the week.
- **Live Occupancy**: Captures "Currently busy" status if available.
- **Multiple Inputs**: Reads search queries from a text file.
- **Data Export**: Saves results to `popular_times.json` and `popular_times.xlsx`.

## Prerequisites
- Python 3.x
- Google Chrome browser

## Installation

1. Clone the repository:
   ```bash
   git clone https://github.com/rv0627/google-maps-popular-times-scraper.git
   cd google-maps-popular-times-scraper
   ```

2. Install dependencies:
   ```bash
   pip install selenium webdriver-manager pandas openpyxl
   ```

## Usage

1. Create a `queries.txt` file in the project directory. Add one search query per line, for example:
   ```text
   Coffee shops in New York
   Gyms in London
   ```

2. Run the scraper:
   ```bash
   python scraper.py
   ```

## Output
The script will generate two files in the project directory:
- **popular_times.json**: Detailed structured data including raw text.
- **popular_times.xlsx**: A flattened table with columns for Place Name, URL, Day, Hour, and Occupancy %.

## Disclaimer
This tool is for educational purposes only. extracting data from Google Maps may violate their Terms of Service. Use responsibly.
