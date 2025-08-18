import re
from pathlib import Path
import whisper
import regex as regex
from deepmultilingualpunctuation import PunctuationModel



def main():
    ######## CONFIGURATION ########
    INPUT_AUDIO_FOLDER = Path("__input_audios")
    OUTPUT_TRANSCRIPT_FOLDER = Path("transcripts")
    ASR_MODEL = whisper.load_model("large")
    PUNCT_MODEL = PunctuationModel()
    ###############################



    process_audio_folder(INPUT_AUDIO_FOLDER, OUTPUT_TRANSCRIPT_FOLDER, ASR_MODEL, PUNCT_MODEL)



def transcribe_audio(audio_path: Path, asr_model):
    print(f"transcribing: {audio_path}")
    result = asr_model.transcribe(str(audio_path), language="en")
    return result["text"]


def clean_text(text: str) -> str:

    # remove auto punctuation (will re-punctuate later)
    text = text.replace(". ", " ").replace("? ", " ").replace("! ", " ").replace(", ", " ")

    # remove non-Latin characters
    text = regex.sub(r'[^\p{Latin}\d\p{P}\s]', '', text)

    # normalize whitespace
    text = re.sub(r'\s+', ' ', text)

    return text.strip()



def punctuate_and_save(raw_text: str, transcript_txt_path: Path, punct_model):
    print(f"cleaning: {transcript_txt_path}")
    cleaned_text = clean_text(raw_text)

    print(f"punctuating: {transcript_txt_path}")
    punctuated_text = punct_model.restore_punctuation(cleaned_text)

    with open(transcript_txt_path, "w", encoding="utf-8") as f:
        f.write(punctuated_text)



def process_audio_folder(audio_folder: Path, transcript_folder: Path, asr_model, punct_model):

    transcript_folder.mkdir(parents=True, exist_ok=True)

    for audio_file in audio_folder.rglob("*.wav"):
        print(f"\nprocessing: {audio_file}")
        stem = audio_file.stem

        transcript_txt_path = transcript_folder / f"{stem}.txt"

        # transcribe audio
        raw_text = transcribe_audio(audio_file, asr_model)

        # punctuate and save
        punctuate_and_save(raw_text, transcript_txt_path, punct_model)




if __name__ == "__main__":
    main()
