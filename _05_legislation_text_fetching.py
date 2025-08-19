import pandas as pd
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, NoSuchElementException
from pathlib import Path
import time
from datetime import datetime


def main():
    ######## CONFIGURATION ########
    INPUT_LEGISLATION_FOLDER = Path("legislations")
    START_DAY = datetime.strptime("20250331", "%Y%m%d")
    END_DAY = datetime.strptime("20250404", "%Y%m%d")
    TAB_XPATH = '//li[contains(@class, "rtsLI") and contains(@class, "rtsLast")]//span[contains(@class, "rtsTxt") and text()="Text"]/ancestor::li'
    TEXT_ID = "ctl00_ContentPlaceHolder1_pageText"
    ###############################

    # headless scraper
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")

    driver = webdriver.Chrome(options=chrome_options)

    fetch_text(INPUT_LEGISLATION_FOLDER, START_DAY, END_DAY, TAB_XPATH, TEXT_ID, driver)


def fetch_text(input_folder: Path, start_day: datetime, end_day: datetime, tab_xpath: str, text_id, driver):
    """
    Fetches the text of legislations on the Legistar webpage and saves with corresponding item and link.

    Parameters:
    - input_folder (Path): Path object of folder containing CSVs with links to legislations texts. Also where legislations texts will be saved.
    - start_day (datetime): datetime object of earliest day in timeframe.
    - end_day (datetime): datetime object of latest day in timeframe. 
    - tab_xpath (str): str object of xpath to switch Legistar webpage to display text of legislation.
    - text_id (str): str object of id of element containing text of legislation on webpage.
    - driver: web driver object.
    """
    try:
        for csv_file in sorted(input_folder.rglob("*.csv")):
            meeting_date = str(csv_file.name).split("_")[0]
            meeting_datetime = datetime.strptime(meeting_date, "%Y%m%d")

            # skip, out of time frame
            if not (start_day <= meeting_datetime <= end_day):
                continue

            
            print(f"processing file: {csv_file}")
            df = pd.read_csv(csv_file)

            if "link" not in df.columns:
                print(f"!!! error with CSV file: {csv_file}.")
                continue

            texts = []

            for _, url in enumerate(df["link"]):
                print(f"opening legislation url: {url}")
                try:
                    driver.get(url)
                    wait = WebDriverWait(driver, 5)

                    # click the "Text" tab
                    tab_element = wait.until(EC.element_to_be_clickable((By.XPATH, tab_xpath)))
                    tab_element.click()


                    # check and access element containing text
                    content_div = wait.until(EC.visibility_of_element_located((By.ID, text_id)))
                    text_content = content_div.text.strip()

                    # check for "Click here for full text" link
                    try:
                        full_text_link = content_div.find_element(By.LINK_TEXT, "Click here for full text")
                        if full_text_link:
                            full_text_url = full_text_link.get_attribute("href")
                            print(f"    Found full text link, navigating to {full_text_url}")
                            driver.get(full_text_url)

                
                            content_div = wait.until(EC.visibility_of_element_located((By.ID, text_id)))
                            text_content = content_div.text.strip()
                    except (TimeoutException, NoSuchElementException):
                        # text not long enough to have "Click here for full text" link
                        pass

                    print(f"retrieved text length: {len(text_content)}")
                    texts.append(text_content)

                except Exception:
                    print(f"!!! error processing url: {url}")
                    # default value
                    texts.append("NO_LEGISLATION")

                time.sleep(1) 


            df["text"] = texts
            df.to_csv(csv_file, index=False)
            print(f"saved with legislation texts: {csv_file}")

    finally:
        driver.quit()


if __name__ == "__main__":
    main()