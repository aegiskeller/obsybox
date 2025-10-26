#!/usr/bin/env python3
"""
Quick test to see what's on a var.astro.cz star page
"""

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from bs4 import BeautifulSoup

# Test with star ID 18765 (G8482.00208)
star_id = "18765"
star_url = f"https://var.astro.cz/en/Stars/{star_id}"

chrome_options = Options()
chrome_options.add_argument("--headless")
chrome_options.add_argument("--no-sandbox")
chrome_options.add_argument("--disable-dev-shm-usage")

driver = webdriver.Chrome(options=chrome_options)

try:
    print(f"Fetching {star_url}...")
    driver.get(star_url)
    
    # Wait for page to load
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "body"))
    )
    
    soup = BeautifulSoup(driver.page_source, 'html.parser')
    
    print("\n=== Page Title ===")
    print(driver.title)
    
    # Test the coordinate extraction
    import re
    page_text = soup.get_text()
    
    print("\n=== Testing coordinate extraction ===")
    coord_pattern = r'RA:\s*(\d{1,2}h\s*\d{2}m\s*\d{2}(?:\.\d+)?s),\s*DE:\s*([+\-]?\d{1,2}°\s*\d{2}\'\s*\d{2}(?:\.\d+)?")'
    match = re.search(coord_pattern, page_text)
    
    if match:
        ra_raw = match.group(1)
        dec_raw = match.group(2)
        print(f"Found RA: {ra_raw}")
        print(f"Found Dec: {dec_raw}")
        
        # Convert to standard format HH:MM:SS.SS
        ra_match = re.match(r'(\d{1,2})h\s*(\d{2})m\s*(\d{2}(?:\.\d+)?)s', ra_raw)
        if ra_match:
            ra_str = f"{ra_match.group(1)}:{ra_match.group(2)}:{ra_match.group(3)}"
            print(f"Converted RA: {ra_str}")
        
        # Convert to standard format ±DD:MM:SS.SS
        dec_match = re.match(r'([+\-]?\d{1,2})°\s*(\d{2})\'\s*(\d{2}(?:\.\d+)?)"', dec_raw)
        if dec_match:
            dec_str = f"{dec_match.group(1)}:{dec_match.group(2)}:{dec_match.group(3)}"
            print(f"Converted Dec: {dec_str}")
    else:
        print("Could not find coordinates with pattern")
    
    print("\n=== All <dt> tags ===")
    for dt in soup.find_all('dt'):
        dd = dt.find_next_sibling('dd')
        if dd:
            print(f"{dt.text.strip()}: {dd.text.strip()}")
    
    print("\n=== All tables ===")
    for i, table in enumerate(soup.find_all('table')):
        print(f"\nTable {i+1}:")
        for row in table.find_all('tr')[:10]:  # First 10 rows
            cells = [cell.text.strip() for cell in row.find_all(['td', 'th'])]
            if cells:
                print(f"  {' | '.join(cells)}")
    
    print("\n=== Raw page text (first 2000 chars) ===")
    print(soup.get_text()[:2000])
    
finally:
    driver.quit()
