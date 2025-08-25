import os
import time
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
import anthropic
from datetime import datetime


def main():
    load_dotenv()

    ######## CONFIGURATION ########
    CLAUDE_KEY = os.getenv("CLAUDE_KEY")
    INPUT_AGENDA_SEGMENTS_FOLDER = Path("agenda_segments")
    OUTPUT_REPORTS_FOLDER = Path("reports")
    START_DAY = datetime.strptime("20250519", "%Y%m%d")
    END_DAY = datetime.strptime("20250523", "%Y%m%d")
    HEADLINE_MODEL = "claude-sonnet-4-20250514"
    SUMMARY_MODEL = "claude-sonnet-4-20250514"
    RATE_LIMIT_SECONDS = 10
    ###############################

    claude_client = anthropic.Anthropic(api_key=CLAUDE_KEY)
    generate_headlines_summaries(INPUT_AGENDA_SEGMENTS_FOLDER, OUTPUT_REPORTS_FOLDER, START_DAY, END_DAY, HEADLINE_MODEL, SUMMARY_MODEL, RATE_LIMIT_SECONDS, claude_client)


def build_headline_prompt(combined_segment: str):
    return f"""
You are a local government reporter covering city council meetings.

You will receive:
- A section from a **city council meeting agenda** (note: this may be vague or generic)
- A section from the related **official legislation**
- A section from the **meeting transcript**

Your task is to write a **clear, one-sentence headline** that:
- Focuses on the **most newsworthy action or decision**
- Summarizes what the **council actually did**, proposed, debated, or approved
- Highlights **specific outcomes**, impacts, or controversial statements
- Is written at an **eighth-grade reading level**
- Contains **no commentary** or extra background

Do *not* copy or paraphrase the agenda title. Use the transcript and legislation instead.

---
{combined_segment}

Headline:
"""


def build_summary_prompt(headline: str, combined_segment: str):
    return f"""
You are a beat reporter covering public meetings.

Given:
- A section from the **meeting agenda**
- Related **official legislation**
- A **meeting transcript segment**
- A **headline** summarizing the segment

Write a **bullet-point summary** that:
- Focuses only on the topic described in the headline
- Uses relevant context from the transcript and agenda
- Clarifies or expands on important details (specific figures, decisions)
- Ignores unrelated discussion
- Is at an **eighth-grade reading level**

---
{combined_segment}

Headline:
{headline}

Summary:
"""


def generate_headline_claude(combined_segment: str, headline_model: str, client):
    """
    Prompts Claude to generate headline from combined segment.

    Parameters:
    - combined_segment (str): string object containing combined segment.
    - headline_model (str): string object of Claude model alias to generate headlines.
    - client: Claude API client. 
    """
    response = client.messages.create(
        model=headline_model,
        max_tokens=64,
        temperature=0,
        messages=[{"role": "user", "content": build_headline_prompt(combined_segment)}]
    )
    return response.content[0].text.strip()


def generate_summary_claude(headline: str, combined_segment: str, summary_model: str, client):
    """
    Prompts Claude to generate summary from headline and combined segment.

    Parameters:
    - headline (str): string object containing headline for combined_segment.
    - combined_segment (str): string object containing combined segment.
    - summary_model (str): string object of Claude model alias to generate summaries.
    - client: Claude API client. 
    """
    prompt = build_summary_prompt(headline, combined_segment)
    response = client.messages.create(
        model=summary_model,
        max_tokens=4096,
        temperature=0,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()


def generate_headlines_summaries(input_agenda_segments_folder: Path, output_reports_folder: Path, start_day: datetime, end_day: datetime, headline_model: str, summary_model: str, rate_limit_seconds: int, client):
    """
    Iterates through all combined segments in time frame within folder and generates headlines and summaries.

    Parameters:
    - input_agenda_segments_folder (Path): Path object of folder containing combined segments.
    - output_reports_folder (Path): Path object of folder where reports (headlines and summaries) are saved.
    - start_day (datetime): datetime object of earliest day in timeframe.
    - end_day (datetime): datetime object of latest day in timeframe.
    - headline_model (str): string object of Claude model alias to generate headlines.
    - summary_model (str): string object of Claude model alias to generate summaries.
    - rate_limit_seconds (int): int object of number of seconds for Claude to sleep between prompts.
    - client: Claude API client.
    """
    output_reports_folder.mkdir(parents=True, exist_ok=True)

    for input_path in sorted(input_agenda_segments_folder.rglob("*.csv")):
        meeting_date = str(input_path.name).split("_")[0]
        meeting_datetime = datetime.strptime(meeting_date, "%Y%m%d")

        # skip, out of time frame
        if not (start_day <= meeting_datetime <= end_day):
            continue

        print(f"processing: {input_path}")

        output_path = output_reports_folder / input_path.name

        # use output file if it exists to not restart progress
        active_path = output_path if output_path.exists() else input_path
        df = pd.read_csv(active_path)

        # create columns if missing 
        if "headline" not in df.columns:
            df["headline"] = "NO_HEADLINE"
        if "summary" not in df.columns:
            df["summary"] = "NO_SUMMARY"

        for idx, row in df.iterrows():
            combined_segment = row["combined_segment"]

            # skip, no segment exists
            if combined_segment == "NO_SEGMENT":
                print(f"skipping row {idx}, no segment")
                continue

            # skip, already done
            if row["headline"] != "NO_HEADLINE":
                print(f"skipping row {idx}, already done")
                continue

            print(f"processing row {idx}")

            try:
                time.sleep(rate_limit_seconds)
                # generate headline
                headline = generate_headline_claude(combined_segment, headline_model, client)

                # generate summary
                summary = generate_summary_claude(headline, combined_segment, summary_model, client)

                df.at[idx, "headline"] = headline
                df.at[idx, "summary"] = summary

            except Exception as e:
                print(f"error processing row {idx}: {e}")
                continue

        df.to_csv(output_path, index=False)


if __name__ == "__main__":
    main()
