from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time
import re

def extract_gpa_number(text: str) -> float | None:
    """Extracts GPA float value from a string like 'GPA: 3.9 (unweighted)'."""
    match = re.search(r"(\d\.\d{1,2})", text)
    return float(match.group(1)) if match else None

def scrape_college_gpa(college_name: str) -> dict:
    slug = college_name.strip().replace(" ", "-")
    url = f"https://www.collegedata.com/college/{slug}"

    options = Options()
    options.add_argument("--headless")
    options.add_argument("--disable-gpu")
    options.add_argument("--no-sandbox")

    driver = webdriver.Chrome(options=options)
    driver.get(url)

    try:
        try:
            driver.find_element(By.ID, 'onetrust-accept-btn-handler').click()
        except:
            pass

        time.sleep(3)  # Allow page to fully render

        # First: Search common GPA block with semantic label
        gpa_elements = driver.find_elements(By.CLASS_NAME, "TitleValue_value__1JT0d")
        for elem in gpa_elements:
            if "GPA" in elem.text:
                gpa_value = extract_gpa_number(elem.text)
                if gpa_value:
                    return {
                        "college": college_name,
                        "gpa": gpa_value
                    }

        # Second: Fallback to table label/value pairing
        labels = driver.find_elements(By.CLASS_NAME, "cd-table__cell-label")
        values = driver.find_elements(By.CLASS_NAME, "cd-table__cell-value")

        for label, value in zip(labels, values):
            if "GPA" in label.text:
                gpa_value = extract_gpa_number(value.text)
                if gpa_value:
                    return {
                        "college": college_name,
                        "gpa": gpa_value
                    }

        return {"college": college_name, "gpa": "Not found"}

    except Exception as e:
        return {"college": college_name, "error": str(e)}
    finally:
        driver.quit()
