from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import json
import time
import os

# Setup Chrome options
options = Options()
options.headless = False  # Set to True if you don't want browser window
options.add_argument("--disable-gpu")
options.add_argument("--no-sandbox")
options.add_argument("--window-size=1920,1080")

driver = webdriver.Chrome(options=options)

url = "https://www.collegedata.com/college-search/"
filename = "collegedata_urls_selenium.json"

# Load existing data
if os.path.exists(filename):
    with open(filename, "r") as f:
        college_links = json.load(f)
else:
    college_links = {}

seen_urls = set(college_links.values())

try:
    driver.get(url)
    time.sleep(5)  # Let page load initially

    last_height = driver.execute_script("return document.body.scrollHeight")
    unchanged_scrolls = 0
    max_unchanged_scrolls = 25  # Stop if no changes this many times
    max_total_scrolls = 500     # Hard cap on total scroll attempts
    total_scrolls = 0

    while total_scrolls < max_total_scrolls:
        print(f"⬇️ Scroll #{total_scrolls + 1}")
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(5)  # Let new data load

        new_height = driver.execute_script("return document.body.scrollHeight")

        links = driver.find_elements(By.CSS_SELECTOR, "a.Link_link__a-VS4.Link_headerLink__2o8d9")
        new_found = 0

        for link in links:
            name = link.text.strip()
            href = link.get_attribute("href")
            if name and href and href not in seen_urls:
                key = f"{name.lower()} ({href.split('/')[-1]})"
                college_links[key] = href
                seen_urls.add(href)
                new_found += 1
                print(f"✅ Added: {name} -> {href}")

                # Save immediately
                with open(filename, "w") as f:
                    json.dump(college_links, f, indent=2)

        if new_found == 0 and new_height == last_height:
            unchanged_scrolls += 1
            print(f"⚠️ No new colleges and no scroll height change ({unchanged_scrolls}/{max_unchanged_scrolls})")
        else:
            unchanged_scrolls = 0

        if unchanged_scrolls >= max_unchanged_scrolls:
            print("✅ No more new content — scraping complete.")
            break

        last_height = new_height
        total_scrolls += 1

    print(f"\n🎓 Total unique colleges found: {len(college_links)}")
    print(f"💾 All saved to: {filename}")

finally:
    driver.quit()
