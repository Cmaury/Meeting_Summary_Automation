import requests
from bs4 import BeautifulSoup
from pathlib import Path
from urllib.parse import urljoin
import csv
import re


def main():
    ######## CONFIGURATION ########
    INPUT_URL_FOLDER = Path("__input_urls")
    OUTPUT_LEGISLATION_FOLDER = Path("legislations")
    TABLE_ID = "ctl00_ContentPlaceHolder1_gridMain_ctl00"
    ###############################


    fetch_links(INPUT_URL_FOLDER, OUTPUT_LEGISLATION_FOLDER, TABLE_ID)


def fetch_links(input_folder: Path, output_folder: Path, table_id: str):
    """
    Finds and stores the URLs to legislations for each meeting in input folder and stores as CSV in output folder.

    Parameters:
    - input_folder (Path): Path object of folder containing URLs to Legistar Meeting Details webpage.
    - output_folder (Path): Path object of folder where CSV of legislation URLs will be saved to.
    - table_id (str): str object of element ID containing table of items (bills, proclamations, etc) on Meeting Details webpage.
    """
    output_folder.mkdir(exist_ok=True, parents=True)

    # iterate through each TXT file
    for txt_file in input_folder.glob("*.txt"):

        # extract url from TXT file
        with open(txt_file, "r", encoding="utf-8") as f:
            page_url = f.read().strip()

        if not page_url:
            print(f"!!! skipping empty file: {txt_file}")
            continue


        # load webpage
        print(f"processing: {page_url}")

        try:
            response = requests.get(page_url, headers={"User-Agent": "Mozilla/5.0"})
            response.raise_for_status()
        except Exception as e:
            print(f"!!! webpage fail: {page_url}")
            continue

        soup = BeautifulSoup(response.text, "html.parser")



        # extract table from webpage using table_id
        table = soup.find("table", id=table_id)
        if not table:
            print(f"No table with id '{table_id}' found on page.")
            continue

        output_csv_path = output_folder / f"{txt_file.stem}.csv"


        # extract and save URLs of legislation and their corresponding item
        with open(output_csv_path, "w", newline="", encoding="utf-8") as csvfile:
            writer = csv.writer(csvfile)
            writer.writerow(["item", "link"])

            # iterate table rows
            for row in table.find_all("tr"):
                cells = row.find_all("td")
                if not cells:
                    continue

                first_col = cells[0]
                text = re.sub(r"[a-zA-Z\s]", "", first_col.get_text(strip=True))
                links = first_col.find_all("a", href=True)

                for a in links:
                    href = urljoin(page_url, a["href"])
                    if text and href:
                        writer.writerow([text, href])

        print(f"saved CSV: {output_csv_path}")


if __name__ == "__main__":
    main()