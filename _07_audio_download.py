import yt_dlp
from pathlib import Path
from datetime import datetime


def main():
    ######## CONFIGURATION ########
    INPUT_YT_LINK_FOLDER = Path("__input_youtube_urls")
    OUTPUT_AUDIO_FOLDER = Path("audios")
    START_DAY = datetime.strptime("20250428", "%Y%m%d")
    END_DAY = datetime.strptime("20250502", "%Y%m%d")
    ###############################

    process_txt_files(INPUT_YT_LINK_FOLDER, OUTPUT_AUDIO_FOLDER, START_DAY, END_DAY)


def download_wav(youtube_url: str, output_file: Path):
    """
    Uses yt_dlp to download audio WAV file from YouTube URL.

    Parameters:
    - youtube_url (str): string object containing YouTube URL of meeting.
    - output_file (Path): Path object of folder where WAV audio file is saved. 
    """
    ydl_opts = {
        "format": "bestaudio/best",
        "postprocessors": [
            {
                "key": "FFmpegExtractAudio",
                "preferredcodec": "wav",
                "preferredquality": "0",
            }
        ],
        "outtmpl": str(output_file.with_suffix("")),  
    }

    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
        ydl.download([youtube_url])

def process_txt_files(input_folder: Path, output_folder: Path, start_day: datetime, end_day: datetime):
    """
    Reads YouTube URL from TXT files and downloads audios as WAV file. 

    Parameters:
    - input_folder (Path): Path object of folder containing TXT files with YouTube URLs (one per file).
    - output_folder (Path): Path object of folder where WAV files will be saved.
    - start_day (datetime): datetime object of earliest day in timeframe.
    - end_day (datetime): datetime object of latest day in timeframe. 
    """
    output_folder.mkdir(parents=True, exist_ok=True)

    for txt_file in sorted(input_folder.glob("*.txt")):
        meeting_date = str(txt_file.name).split("_")[0]
        meeting_datetime = datetime.strptime(meeting_date, "%Y%m%d")

        # skip, out of time frame
        if not (start_day <= meeting_datetime <= end_day):
            continue
        
        output_file = output_folder / f"{txt_file.stem}.wav"

        # skip, already exists
        if output_file.exists():
            print(f"skipping, already exists: {txt_file}")
            continue

    
        link = txt_file.read_text().strip()

        # skip, no URL in TXT file
        if not link:
            print(f"!!! empty file: {txt_file}")
            continue

        
        print(f"downloading: {txt_file}")
        download_wav(link, output_file)

if __name__ == "__main__":
    main()
