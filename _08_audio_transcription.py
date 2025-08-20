import re
from pathlib import Path
import whisper
import regex as regex
from deepmultilingualpunctuation import PunctuationModel
from datetime import datetime



def main():
    ######## CONFIGURATION ########
    INPUT_AUDIO_FOLDER = Path("audios")
    OUTPUT_TRANSCRIPT_FOLDER = Path("transcripts")
    START_DAY = datetime.strptime("20250505", "%Y%m%d")
    END_DAY = datetime.strptime("20250509", "%Y%m%d")
    ASR_MODEL = whisper.load_model("large")
    PUNCT_MODEL = PunctuationModel()
    ###############################



    process_audio_folder(INPUT_AUDIO_FOLDER, OUTPUT_TRANSCRIPT_FOLDER, START_DAY, END_DAY, ASR_MODEL, PUNCT_MODEL)



def transcribe_audio(audio_path: Path, asr_model):
    """
    Transcribes WAV audio file using Whisper.

    Parameters:
    - audio_path (Path): Path object of WAV file.
    - asr_model: Whisper audio transcription model.
    """
    print(f"transcribing: {audio_path}")
    result = asr_model.transcribe(str(audio_path), language="en")
    return result["text"]


def clean_text(text: str):
    """
    Cleans transcript text by removing punctuation, non-Latin characters, normalizing whitespace, and removing some filler words.

    Parameters:
    - text (str): Transcript text to be cleaned.
    """

    # remove auto punctuation (will re-punctuate later)
    text = text.replace(". ", " ").replace("? ", " ").replace("! ", " ").replace(", ", " ")

    # remove non-Latin characters
    text = regex.sub(r'[^\p{Latin}\d\p{P}\s]', '', text)

    # normalize whitespace
    text = re.sub(r'\s+', ' ', text)

    # remove filler words
    text = re.sub(r'\b(?:uh|um)+\b[,.]?\s*', '', text, flags=re.IGNORECASE)

    return text.strip()



def punctuate_and_save(raw_text: str, transcript_txt_path: Path, punct_model):
    """
    Punctuates transcript text and saves to TXT file. 

    Parameters:
    - raw_text (str): Raw transcript text with no punctuation.
    - transcript_txt_path (Path): Path object of destination file where transcript will be saved.
    - punct_model: deepmultilingualpunctuation model.
    """
    print(f"cleaning: {transcript_txt_path}")
    cleaned_text = clean_text(raw_text)

    print(f"punctuating: {transcript_txt_path}")
    punctuated_text = punct_model.restore_punctuation(cleaned_text)

    with open(transcript_txt_path, "w", encoding="utf-8") as f:
        f.write(punctuated_text)



def process_audio_folder(audio_folder: Path, transcript_folder: Path, start_day: datetime, end_day: datetime, asr_model, punct_model):
    """
    Transcribes, cleans, punctuates, and saves audios WAV files to transcript TXT files.

    Parameters:
    - audio_folder (Path): Path object of folder containining WAV audio files.
    - transcript_folder (Path): Path object of destination folder where transcript TXT files will be saved.
    - start_day (datetime): datetime object of earliest day in timeframe.
    - end_day (datetime): datetime object of latest day in timeframe. 
    - asr_model: Whisper audio transcription model.
    - punct_model: deepmultilingualpunctuation model.
    """
    transcript_folder.mkdir(parents=True, exist_ok=True)

    for audio_file in sorted(audio_folder.rglob("*.wav")):
        meeting_date = str(audio_file.name).split("_")[0]
        meeting_datetime = datetime.strptime(meeting_date, "%Y%m%d")

        # skip, out of time frame
        if not (start_day <= meeting_datetime <= end_day):
            continue

        print(f"\nprocessing: {audio_file}")
        stem = audio_file.stem

        transcript_txt_path = transcript_folder / f"{stem}.txt"

        # transcribe audio
        raw_text = transcribe_audio(audio_file, asr_model)

        # punctuate and save
        punctuate_and_save(raw_text, transcript_txt_path, punct_model)




if __name__ == "__main__":
    main()
