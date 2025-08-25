from dotenv import load_dotenv
import anthropic
import json
import csv
from pathlib import Path
import os
import pandas as pd
from datetime import datetime


def main():
    load_dotenv()

    ######## CONFIGURATION ########
    CLAUDE_KEY = os.getenv("CLAUDE_KEY")
    INPUT_TRANSCRIPT_FOLDER = Path("transcripts")
    INPUT_AGENDA_SEGMENTS_FOLDER = Path("agenda_segments")
    OUTPUT_TRANSCRIPT_SEGMENTS_FOLDER = Path("transcript_segments")
    START_DAY = datetime.strptime("20250519", "%Y%m%d")
    END_DAY = datetime.strptime("20250523", "%Y%m%d")
    SEGMENTATION_MODEL = "claude-3-7-sonnet-20250219"
    ################################

    client = anthropic.Anthropic(api_key=CLAUDE_KEY)

    segment_all_transcripts(
        INPUT_TRANSCRIPT_FOLDER,
        INPUT_AGENDA_SEGMENTS_FOLDER,
        OUTPUT_TRANSCRIPT_SEGMENTS_FOLDER, 
        START_DAY, 
        END_DAY,
        SEGMENTATION_MODEL,
        client
    )


def transcript_segmentation_prompt(text: str):
    return f"""
You are given:
1. The transcript of a city council meeting.
2. A list of agenda items with their full text.

Your task:
- Segment the transcript into passages, assigning each passage to the agenda item it most closely relates to.
- The meeting may not have followed the agenda in exact order, so match passages based on content, not position in the list.
- An agenda item can appear multiple times in different parts of the transcript if the discussion returns to it.
- Keep transcript text exactly as in the input (no paraphrasing).
- Return the output as **strict JSON only**, parsable by Python's json.loads().
- Do not include any explanations, notes, markdown, code fences, or commentary — output ONLY the JSON array.

Output format (must be exactly JSON, no extra text):
[
  {{"agenda_item": "Agenda Item 4: Proclamation 2022-1222", "transcript": <exact text>}},
  {{"agenda_item": "Agenda Item 2: Pledge of Allegiance", "transcript": <exact text>}}
]

Here is the combined agenda + transcript text:
\"\"\"
{text}
\"\"\"
    """.strip()




def claude_segment(transcript_text: str, segmentation_model: str, client):
    """
    Prompts Claude to segment transcript into transcript segments.

    Parameters:
    - transcript_text (str): String containing text from meeting transcript and list of agenda items.
    - client: Claude API client.
    """
    prompt = transcript_segmentation_prompt(transcript_text)
    
    stream = client.messages.create(
        model=segmentation_model,
        max_tokens=64000,
        temperature=0,
        stream=True,
        messages=[{"role": "user", "content": prompt}]
    )
    
    response_text = ""
    for chunk in stream:
        if chunk.type == "content_block_delta":
            response_text += chunk.delta.text
    
    return response_text.strip()


def save_json_segments_to_csv(json_string: str, output_path: Path):
    """
    Processes LLM response as JSON string and saves to output path.

    Parameters:
    - json_string (str): String parsable as JSON.
    - output_path (Path): Path object of destination CSV file.
    """
    try:
        data = json.loads(json_string)
        if not isinstance(data, list):
            raise ValueError("!!! not list of JSON objects")

        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["agenda_item", "transcript"])
            writer.writeheader()
            for row in data:
                writer.writerow({
                    "agenda_item": row.get("agenda_item", ""),
                    "transcript": row.get("transcript", "")
                })
        print(f"saved: {output_path}")

    except json.JSONDecodeError as e:
        print(f"!!! JSON parsing error: {e}")
        with open(str(output_path).replace(".csv", ".txt"), "w", encoding="utf-8") as f:
            f.write(json_string)



def segment_all_transcripts(input_folder: Path, agenda_folder: Path, output_folder: Path, start_day: datetime, end_day: datetime, segmentation_model: str, client):
    """
    Prompts Claude to segment TXT meeting transcripts and saves segments as CSV.

    Parameters:
    - input_folder (Path): Path object of folder with TXT transcript files.
    - agenda_folder (Path): Path object of folder with CSV agenda segments.
    - output_folder (Path): Path object of folder where CSV segment files will be saved.
    - start_day (datetime): datetime object of earliest day in timeframe.
    - end_day (datetime): datetime object of latest day in timeframe. 
    - segmentation_model (str): string object of Claude model alias to segment.
    - client: Claude API client. 
    """

    output_folder.mkdir(parents=True, exist_ok=True)

    for file_path in sorted(input_folder.rglob("*.txt")):
        meeting_date = str(file_path.name).split("_")[0]
        meeting_datetime = datetime.strptime(meeting_date, "%Y%m%d")

        # skip, out of time frame
        if not (start_day <= meeting_datetime <= end_day):
            continue

        file_stem = file_path.stem
        agenda_path = agenda_folder / f"{file_stem}.csv"
        output_path = output_folder / f"{file_stem}.csv"

        if output_path.exists():
            print(f"skipping, already exists: {file_path}")
            continue


        print(f"segmenting: {file_path}")


        text = "Meeting Transcript:\n" + file_path.read_text(encoding='utf-8')

        agenda_segments = list(pd.read_csv(agenda_path)["agenda_segment"])
        for i in range(len(agenda_segments)):
            text += f"\n\nAgenda Item {i+1}:\n" + agenda_segments[i]


        # replace double quotes for JSON parsing
        text = text.replace('"', "'")

        segments_json = claude_segment(text, segmentation_model, client)
        save_json_segments_to_csv(segments_json, output_path)


if __name__ == "__main__":
    main()
