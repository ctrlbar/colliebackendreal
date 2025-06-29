from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from rapidfuzz import process, fuzz
import json
import time
import re

# Load your JSON of college name-to-URL
with open("collegedata_urls_selenium.json") as f:
    college_url_map = json.load(f)

def extract_gpa_number(text: str) -> float | None:
    match = re.search(r"(\d+(\.\d{1,2})?)", text)
    return float(match.group(1)) if match else None

def find_best_college_match(user_input: str) -> tuple[str, str] | None:
    user_input = user_input.lower().strip()
    keys = list(college_url_map.keys())
    cleaned_keys = [k.split(" (")[0].lower() for k in keys]

    match, score, idx = process.extractOne(user_input, cleaned_keys, scorer=fuzz.partial_ratio)
    best_key = keys[idx]

    print(f"[DEBUG] Input: '{user_input}' → Match: '{best_key}' (score: {score})")

    if score >= 85:
        return best_key, college_url_map[best_key]

    return None


def scrape_college_gpa(user_input: str) -> dict:
    matched = find_best_college_match(user_input)
    if not matched:
        return {"input": user_input, "error": "No close college match found."}

    college_name, url = matched

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=options)
    driver.get(url)

    try:
        try:
            driver.find_element(By.ID, 'onetrust-accept-btn-handler').click()
        except:
            pass

        time.sleep(3)

        titles = driver.find_elements(By.CLASS_NAME, "TitleValue_title__2-afK")
        values = driver.find_elements(By.CLASS_NAME, "TitleValue_value__1JT0d")

        for title, value in zip(titles, values):
            if "average gpa" in title.text.lower():
                gpa_value = extract_gpa_number(value.text)
                if gpa_value is not None:
                    print(f"[DEBUG] Matched GPA Label: '{title.text}' → GPA: {gpa_value}")
                    return {"college": college_name, "gpa": gpa_value}
                


        labels = driver.find_elements(By.CLASS_NAME, "cd-table__cell-label")
        values = driver.find_elements(By.CLASS_NAME, "cd-table__cell-value")
        for label, value in zip(labels, values):
            if "GPA" in label.text:
                gpa_value = extract_gpa_number(value.text)
                if gpa_value:
                    return {"college": college_name, "gpa": gpa_value}

        return {"college": college_name, "gpa": "Not found"}

    except Exception as e:
        return {"college": college_name, "error": str(e)}
    finally:
        driver.quit()
