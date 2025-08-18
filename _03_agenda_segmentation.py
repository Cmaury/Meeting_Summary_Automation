from dotenv import load_dotenv
import anthropic
import json
import csv
from pathlib import Path
import os



def main():
    load_dotenv()

    ######## CONFIGURATION ########
    CLAUDE_KEY = os.getenv("CLAUDE_KEY")
    INPUT_PROCESSED_AGENDA_FOLDER = Path("agendas_processed")
    OUTPUT_AGENDA_SEGMENTS_FOLDER = Path("agenda_segments")
    ################################


    client = anthropic.Anthropic(api_key=CLAUDE_KEY)

    segment_all_agendas(INPUT_PROCESSED_AGENDA_FOLDER, OUTPUT_AGENDA_SEGMENTS_FOLDER, client)



def agenda_segmentation_prompt(agenda_text: str):
    return f"""
You are a professional city council meeting assistant.

Given the full raw text of a meeting agenda, segment it into distinct agenda items. For each item:

1. Include the full agenda item title (e.g., "Bill 2023-114: Amending the zoning regulations").
2. Each **bill, paper, resolution, or ordinance** (e.g., "ORD. 2023-114", "RES. 2023-R016", "PAPER #412") counts as a **separate agenda item**, even if multiple items fall under the same section.
3. If a bill number or ordinance number appears, include it as part of the agenda item title.
4. Under each agenda item, include **all the text** that falls under it until the next agenda item begins.
5. Keep the original wording and formatting. Do not summarize or shorten the text.
6. Do not skip or omit any part of the agenda. This includes routine items such as “Roll Call,” “Public Comment," and other procedural sections.

Return the segmented agenda as a JSON array of strings. Each string is one agenda item with its full text.

**Important:** Return **only** the JSON array of strings with no additional text, explanation, or commentary. The output must be a valid JSON array.

[
  "[Agenda item title]\\n   [Full text under the item]",
  "[Next agenda item]\\n   [Full text under the item]",
  ...
]

Agenda:
\"\"\"{agenda_text}\"\"\"
"""




def claude_segment(agenda_text: str, client):
    """
    Claude prompt wrapper function.

    Parameters:
    - agenda_text (str): String containing extracted text from meeting agenda.
    - client: Claude API client.
    """
    prompt = agenda_segmentation_prompt(agenda_text)
    response = client.messages.create(
        model="claude-3-5-haiku-20241022",
        max_tokens=8192,
        temperature=0,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()





def save_json_segments_to_csv(json_string: str, output_path: Path):
    """
    Processes LLM response as JSON string and saves to output path.

    Parameters:
    - json_string (str): String parsable as JSON.
    - output_path (Path): Path object of destination JSON file.
    """
    try:
        segments = json.loads(json_string)
        with output_path.open("w", newline='', encoding='utf-8') as f:
            writer = csv.writer(f)
            writer.writerow(["agenda_segment"])
            for segment in segments:
                writer.writerow([segment])
        print(f"saved segments to {output_path}")
    except json.JSONDecodeError as e:
        print(f"!!! llm output not JSON parsable")





def segment_all_agendas(input_folder: Path, output_folder: Path, client):
    """
    Prompts Claude to segment TXT meeting agendas and saves segments as CSV.

    Parameters:
    - input_folder (Path): Path object of folder with TXT agenda files.
    - output_folder (Path): Path object of folder where CSV segment files will be saved.
    - client: Claude API client. 
    """
    output_folder.mkdir(parents=True, exist_ok=True)

    for file_path in input_folder.rglob("*.txt"):
        print(f"Segmenting {file_path}")
        file_stem = file_path.stem
        output_path = output_folder / f"{file_stem}.csv"

        text = file_path.read_text(encoding='utf-8')
        segments_json = claude_segment(text, client)
        save_json_segments_to_csv(segments_json, output_path)




if __name__ == "__main__":
    main()
