import pdfplumber
from pathlib import Path
from datetime import datetime


def main():
    ######## CONFIGURATION ########
    INPUT_RAW_AGENDA_FOLDER = Path("agendas_raw")
    OUTPUT_PROCESSED_AGENDA_FOLDER = Path("agendas_processed")
    START_DAY = datetime.strptime("20250505", "%Y%m%d")
    END_DAY = datetime.strptime("20250509", "%Y%m%d")
    ###############################

    process_agendas(INPUT_RAW_AGENDA_FOLDER, OUTPUT_PROCESSED_AGENDA_FOLDER, START_DAY, END_DAY)


def process_pdf_to_text(pdf_path: Path, output_path: Path):
    """
    Extracts text from all pages of a PDF file and writes it to a TXT file.

    Parameters:
    - pdf_path (Path): Path object of the input PDF file.
    - output_path (Path): Path object of where the extracted text will be saved as a TXT file.
    - start_day (datetime): datetime object of earliest day in timeframe.
    - end_day (datetime): datetime object of latest day in timeframe. 
    """
    with pdfplumber.open(pdf_path) as pdf:
        all_text = ""
        for page in pdf.pages:
            page_text = page.extract_text()
            if page_text:
                all_text += page_text + "\n\n"

    output_path.parent.mkdir(parents=True, exist_ok=True)
    output_path.write_text(all_text, encoding="utf-8")


def process_agendas(input_folder: Path, output_folder: Path, start_day: datetime, end_day: datetime):
    """
    Processes all agenda PDF files under a given input folder, extracting text and saving
    each as a corresponding TXT file in the output folder.

    Parameters:
    - input_folder (Path): Path object of folder containing PDF files.
    - output_folder (Path): Path object of folder to save the processed TXT files.
    """
    output_folder.mkdir(parents=True, exist_ok=True)

    for pdf_path in sorted(input_folder.rglob("*.pdf")):
        meeting_date = str(pdf_path.name).split("_")[0]
        meeting_datetime = datetime.strptime(meeting_date, "%Y%m%d")

        # skip, out of time frame
        if not (start_day <= meeting_datetime <= end_day):
            continue
        
        file_stem = pdf_path.stem  
        output_txt_path = output_folder / f"{file_stem}.txt"

        print(f"processing: {pdf_path}")

        # process individual file
        process_pdf_to_text(pdf_path, output_txt_path)


if __name__ == "__main__":
    main()
