import time
import json
import logging
import traceback
import re
import pandas as pd
from selenium import webdriver
from selenium.webdriver.common.by import By
from selenium.webdriver.common.keys import Keys
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager
from selenium.webdriver.chrome.service import Service as ChromeService
from selenium.common.exceptions import TimeoutException, WebDriverException

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

DAYS = ["Sunday", "Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday"]

def get_driver():
    options = webdriver.ChromeOptions()
    # options.add_argument("--headless=new") 
    options.add_argument("--lang=en") 
    options.add_argument("--start-maximized")
    options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    service = ChromeService(ChromeDriverManager().install())
    driver = webdriver.Chrome(service=service, options=options)
    return driver

def parse_popular_times(flat_data):
    """
    Parses a list of strings like "55% busy at 12 PM." into structured data.
    """
    parsed_items = []
    for item in flat_data:
        # Regex to find percentages and time
        match = re.search(r"(\d+)% busy at (\d+)(?:\u202f)?(AM|PM)", item)
        if not match:
            # "0% busy" might be different? "Usually 0%..."
            match = re.search(r"Usually (\d+)% busy at (\d+)(?:\u202f)?(AM|PM)", item)
        
        if match:
             pct = int(match.group(1))
             hour = int(match.group(2))
             ampm = match.group(3)
             if ampm == "PM" and hour != 12:
                 hour += 12
             elif ampm == "AM" and hour == 12:
                 hour = 0
             parsed_items.append({"hour": hour, "occupancy": pct, "raw": item})
        else:
            # "Currently 50% busy"
            match_curr = re.search(r"Currently (\d+)% busy", item)
            if match_curr:
                parsed_items.append({"hour": "Now", "occupancy": int(match_curr.group(1)), "raw": item})
            else:
                 # "0% busy"
                 if "0% busy" in item:
                     parsed_items.append({"hour": "?", "occupancy": 0, "raw": item})

    # Group by days
    days = []
    day_chunk = []
    last_hour = -1
    
    for item in parsed_items:
        h = item["hour"]
        if isinstance(h, int):
            if h < last_hour and last_hour != -1:
                days.append(day_chunk)
                day_chunk = []
            last_hour = h
        day_chunk.append(item)
    
    if day_chunk:
        days.append(day_chunk)
        
    return days

def get_place_urls(driver, query):
    """
    Searches for a query and extracts all place URLs from the results list.
    """
    logging.info(f"Searching for: {query}")
    driver.get("https://www.google.com/maps")
    wait = WebDriverWait(driver, 10)
    
    search_input = None
    selectors = [
        (By.ID, "searchboxinput"),
        (By.NAME, "q"),
        (By.CSS_SELECTOR, "input[aria-label='Search Google Maps']"),
    ]
    
    for by, val in selectors:
        try:
            search_input = wait.until(EC.element_to_be_clickable((by, val)))
            break
        except:
            continue
            
    if not search_input:
        logging.error("Could not find search input.")
        return []

    search_input.clear()
    search_input.send_keys(query)
    search_input.send_keys(Keys.ENTER)
    
    time.sleep(3)
    
    try:
        results_feed = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, "div[role='feed']")))
        
        logging.info("Found results list. Scrolling to load more...")
        
        for _ in range(5): 
            driver.execute_script("arguments[0].scrollTop = arguments[0].scrollHeight", results_feed)
            time.sleep(1.5)
            
        anchors = results_feed.find_elements(By.CSS_SELECTOR, "a[href*='/maps/place/']")
        urls = set()
        for a in anchors:
            href = a.get_attribute("href")
            if href:
                urls.add(href.split("?")[0])
        
        logging.info(f"Found {len(urls)} places.")
        return list(urls)

    except TimeoutException:
        logging.info("No results list found. Checking if single result loaded directly.")
        try:
            current_url = driver.current_url
            if "/maps/place/" in current_url:
                logging.info("Single result found.")
                return [current_url]
        except:
            pass
            
    return []

def scrape_place(driver, url, original_query):
    logging.info(f"Scraping place URL: {url}")
    driver.get(url)
    time.sleep(3) # Wait for load
    
    wait = WebDriverWait(driver, 10)
    place_name = "Unknown"
    try:
        h1 = wait.until(EC.presence_of_element_located((By.TAG_NAME, "h1")))
        place_name = h1.text
        logging.info(f"Place Name: {place_name}")
    except:
        pass

    driver.execute_script("window.scrollBy(0, 500);")
    time.sleep(2)

    bars = driver.find_elements(By.CSS_SELECTOR, "div[aria-label*='busy']")
    if not bars:
        logging.info("No popular times for this place.")
        return None

    visible_data = [b.get_attribute("aria-label") for b in bars]
    parsed_days = parse_popular_times(visible_data)
    
    structured_data = {}
    if len(parsed_days) == 7:
        for i, day_items in enumerate(parsed_days):
            structured_data[DAYS[i]] = day_items
    else:
        structured_data["CollectedData"] = visible_data

    return {
        "query": original_query,
        "name": place_name,
        "url": url,
        "popular_times": structured_data
    }

def main():
    queries = []
    try:
        with open("queries.txt", "r") as f:
            queries = [line.strip() for line in f if line.strip()]
    except FileNotFoundError:
        logging.error("queries.txt not found.")
        return

    all_results = []
    driver = None
    
    try:
        driver = get_driver()
        
        for query in queries:
            urls = get_place_urls(driver, query)
            
            for url in urls:
                try:
                    data = scrape_place(driver, url, query)
                    if data:
                        all_results.append(data)
                except Exception as e:
                    logging.error(f"Error scraping {url}: {e}")
                    continue
                    
    except Exception as e:
        logging.error(f"Fatal error: {e}")
        traceback.print_exc()
    finally:
        if driver:
            driver.quit()

    # Save JSON
    with open("popular_times.json", "w") as f:
        json.dump(all_results, f, indent=4)
    logging.info(f"Scraping completed. Found data for {len(all_results)} places. Saved to popular_times.json")

    # Save Excel
    logging.info("Preparing Excel export...")
    flattened_data = []
    
    for entry in all_results:
        q = entry.get("query")
        n = entry.get("name")
        u = entry.get("url")
        pt = entry.get("popular_times", {})
        
        # Check standard 7 days
        days_found = False
        for day_name in DAYS:
            key = day_name
            if key in pt:
                days_found = True
                for hour_data in pt[key]:
                    flattened_data.append({
                        "Query": q,
                        "Place Name": n,
                        "URL": u,
                        "Day": key,
                        "Hour": hour_data.get("hour"),
                        "Occupancy (%)": hour_data.get("occupancy"),
                        "Raw Text": hour_data.get("raw")
                    })
        
        # If not standard, check CollectedData
        if not days_found and "CollectedData" in pt:
             raw_list = pt["CollectedData"]
             parsed_list = parse_popular_times(raw_list) 
             
             for day_idx, day_items in enumerate(parsed_list):
                 day_label = DAYS[day_idx] if day_idx < 7 else f"Day {day_idx+1}"
                 for hour_data in day_items:
                     flattened_data.append({
                        "Query": q,
                        "Place Name": n,
                        "URL": u,
                        "Day": day_label,
                        "Hour": hour_data.get("hour"),
                        "Occupancy (%)": hour_data.get("occupancy"),
                        "Raw Text": hour_data.get("raw")
                     })

    if flattened_data:
        df = pd.DataFrame(flattened_data)
        
        # Save aggregate
        try:
            df.to_excel("popular_times.xlsx", index=False)
            logging.info("Saved aggregate data to popular_times.xlsx")
        except Exception as e:
            logging.error(f"Could not save aggregate Excel: {e}")

        # Save individual files per query
        unique_queries = df["Query"].unique()
        for query in unique_queries:
            if not query:
                continue
            
            # Sanitize filename
            safe_name = re.sub(r'[\\/*?:"<>|]', "_", str(query))
            filename = f"{safe_name}.xlsx"
            
            query_df = df[df["Query"] == query]
            try:
                query_df.to_excel(filename, index=False)
                logging.info(f"Saved {len(query_df)} rows to {filename}")
            except Exception as e:
                logging.error(f"Could not save {filename}: {e}")
            
    else:
        logging.info("No data to export.")

if __name__ == "__main__":
    main()
