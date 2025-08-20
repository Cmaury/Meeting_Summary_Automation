import requests
from bs4 import BeautifulSoup
from urllib.parse import urljoin
from pathlib import Path
from datetime import datetime



def main():
    ######## CONFIGURATION ########
    INPUT_URLS_FOLDER = Path("__input_legistar_urls")
    OUTPUT_RAW_AGENDA_FOLDER = Path("agendas_raw")
    START_DAY = datetime.strptime("20250505", "%Y%m%d")
    END_DAY = datetime.strptime("20250509", "%Y%m%d")
    LINK_ID = "ctl00_ContentPlaceHolder1_hypMinutes"
    ###############################

    download_agendas_from_urls(INPUT_URLS_FOLDER, OUTPUT_RAW_AGENDA_FOLDER, START_DAY, END_DAY, LINK_ID)



def download_agendas_from_urls(input_folder: Path, output_folder: Path, start_day: datetime, end_day: datetime, link_id: str):
    """
    Downloads agendas from city council website and saves them as PDF files.

    Parameters:
    - input_folder (Path): Path object of folder with txt files containing Legistar Meeting Details URL.
    - output_folder (Path): Path object of folder where PDF files will be saved.
    - start_day (datetime): datetime object of earliest day in timeframe.
    - end_day (datetime): datetime object of latest day in timeframe. 
    - link_id (str): ID of element with link to downloadable PDF on Meeting Details website.
    """
    output_folder.mkdir(parents=True, exist_ok=True)

    # iterate through each meeting
    for txt_file in sorted(input_folder.glob("*.txt")):
        meeting_date = str(txt_file.name).split("_")[0]
        meeting_datetime = datetime.strptime(meeting_date, "%Y%m%d")

        # skip, out of time frame
        if not (start_day <= meeting_datetime <= end_day):
            continue

        with open(txt_file, "r", encoding="utf-8") as f:
            page_url = f.read().strip()

        
        # extract url from file
        if not page_url:
            print(f"!!! issue with url file: {txt_file}")
            continue

        print(f"processing: {page_url}")

        # load url
        try:
            response = requests.get(page_url, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
        except Exception as e:
            print(f"!!! website fail: {page_url}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")


        # find pdf
        link_tag = soup.find("a", id=link_id)
        if not link_tag or not link_tag.get("href"):
            print(f"!!! pdf not found: {page_url}")
            continue

        pdf_url = urljoin(page_url, link_tag["href"])
        print(f"found pdf: {pdf_url}")


        # download pdf
        try:
            pdf_response = requests.get(pdf_url, headers={"User-Agent": "Mozilla/5.0"})
            pdf_response.raise_for_status()
        except Exception as e:
            print(f"!!! pdf download fail: {pdf_url}")
            continue

        output_filename = output_folder / (txt_file.stem + ".pdf")
        with open(output_filename, "wb") as f:
            f.write(pdf_response.content)

        print(f"pdf saved: '{output_filename}'\n")




if __name__ == "__main__":
    main()