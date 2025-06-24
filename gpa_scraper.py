from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
import time

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

        time.sleep(3)  # Let the page fully load

        # NEW: Try locating GPA in TitleValue_value__1JT0d class
        gpa_elements = driver.find_elements(By.CLASS_NAME, "TitleValue_value__1JT0d")
        for elem in gpa_elements:
            if "GPA" in elem.text:
                return {
                    "college": college_name,
                    "gpa": elem.text.strip()
                }

        # Fallback: try label/value table pairing method
        labels = driver.find_elements(By.CLASS_NAME, "cd-table__cell-label")
        values = driver.find_elements(By.CLASS_NAME, "cd-table__cell-value")

        for label, value in zip(labels, values):
            if "GPA" in label.text:
                return {
                    "college": college_name,
                    "gpa": value.text.strip()
                }

        return {"college": college_name, "gpa": "Not found"}

    except Exception as e:
        return {"error": str(e)}
    finally:
        driver.quit()


