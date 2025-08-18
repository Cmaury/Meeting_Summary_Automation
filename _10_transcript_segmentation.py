from dotenv import load_dotenv
import anthropic
import json
import csv
from pathlib import Path
import os
import pandas as pd


def main():
    ######## CONFIGURATION ########
    load_dotenv()
    CLAUDE_KEY = os.getenv("CLAUDE_KEY")
    input_transcript_folder = Path("transcripts")
    agenda_segments_folder = Path("agenda_segments")
    output_transcript_segment_folder = Path("tempy_folder")
    ################################

    client = anthropic.Anthropic(api_key=CLAUDE_KEY)

    segment_all_transcripts(
        input_transcript_folder,
        agenda_segments_folder,
        output_transcript_segment_folder,
        client
    )


def transcript_segmentation_prompt(text: str) -> str:
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




def claude_segment(text: str, client):
    """
    Claude prompt wrapper function with streaming support.

    Parameters:
    - text (str): String containing text from meeting transcript and list of agenda items.
    - client: Claude API client.
    """
    prompt = transcript_segmentation_prompt(text)
    
    # Use streaming for long requests
    stream = client.messages.create(
        model="claude-3-7-sonnet-20250219",  # Updated model name
        max_tokens=64000,
        temperature=0,
        stream=True,  # Enable streaming
        messages=[{"role": "user", "content": prompt}]
    )
    
    # Collect the streamed response
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
            raise ValueError("Expected a list of JSON objects.")

        # Save as CSV
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, mode="w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(f, fieldnames=["agenda_item", "transcript"])
            writer.writeheader()
            for row in data:
                writer.writerow({
                    "agenda_item": row.get("agenda_item", ""),
                    "transcript": row.get("transcript", "")
                })
        print(f"Saved segmented transcript to {output_path}")

    except json.JSONDecodeError as e:
        print(f"Error parsing JSON from Claude: {e}")
        with open(str(output_path).replace(".csv", ".txt"), "w", encoding="utf-8") as f:
            f.write(json_string)



def segment_all_transcripts(input_folder: Path, agenda_folder: Path, output_folder: Path, client):
    """
    Prompts Claude to segment TXT meeting transcripts and saves segments as CSV.

    Parameters:
    - input_folder (Path): Path object of folder with TXT transcript files.
    - agenda_folder (Path): Path object of folder with CSV agenda segments.
    - output_folder (Path): Path object of folder where CSV segment files will be saved.
    - client: Claude API client. 
    """
    for file_path in input_folder.rglob("*.txt"):


        file_stem = file_path.stem
        agenda_path = agenda_folder / f"{file_stem}.csv"
        output_path = output_folder / f"{file_stem}.csv"

        if output_path.exists():
            print(f"Skipping {file_path}")
            continue


        print(f"Segmenting {file_path}")

        
        text = "Meeting Transcript:\n" + file_path.read_text(encoding='utf-8')

        # Append agenda items
        agenda_segments = list(pd.read_csv(agenda_path)["agenda_segment"])
        for i in range(len(agenda_segments)):
            text += f"\n\nAgenda Item {i+1}:\n" + agenda_segments[i]


        print(len(text))
        text = text.replace('"', "'")
        print(len(text))

        segments_json = claude_segment(text, client)
        save_json_segments_to_csv(segments_json, output_path)


if __name__ == "__main__":
    main()
