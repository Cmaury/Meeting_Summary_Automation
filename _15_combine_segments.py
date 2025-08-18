import pandas as pd
from pathlib import Path

TRANSCRIPTS_DIR = Path("transcript_segments")
AGENDAS_DIR = Path("agenda_segments")


def combine_agenda_and_transcript(agenda_path: Path, transcript_path: Path):
    """Merge agenda segments with matching transcript sections based on LLM matching."""

    agenda_df = pd.read_csv(agenda_path)
    transcript_df = pd.read_csv(transcript_path)

    combined_segments = []

    for _, agenda_row in agenda_df.iterrows():
        agenda_summary = agenda_row.get("matching_summary", "NO_SUMMARY")

        # Handle agenda summaries that can't be summarized
        if agenda_summary == "NO_SUMMARY":
            combined_segments.append("NO_SEGMENT")
            continue

        # Initialize section with agenda and legislation
        combined_text = (
            "**Section of meeting agenda:**\n"
            f"{agenda_row.get('agenda_segment', '')}\n\n"
            "**Section of meeting legislation:**\n"
            f"{agenda_row.get('matched_legislation', '')}\n\n"
            "**Section of meeting transcript:**\n"
        )

        found_match = False

        for _, transcript_row in transcript_df.iterrows():
            llm_choice = transcript_row.get("llm_match", 0)

            # Skip unmatched rows
            if isinstance(llm_choice, str) and llm_choice == "NO_SUMMARY":
                continue

            try:
                llm_choice = int(llm_choice)
            except ValueError:
                continue

            if llm_choice not in [1, 2, 3]:
                continue

            selected_summary = transcript_row.get(f"match{llm_choice}_summary", "NO_SUMMARY")
            if selected_summary == agenda_summary:
                combined_text += transcript_row.get("segment", "") + "\n"
                found_match = True

        if not found_match:
            combined_text += "NO_TRANSCRIPT\n"

        combined_segments.append(combined_text)

    # Store results back in DataFrame and save
    agenda_df["manual_combined_segment"] = combined_segments
    agenda_df.to_csv(agenda_path, index=False)
    print(f"Saved: {agenda_path.name}")


def process_all_files():
    for transcript_file in TRANSCRIPTS_DIR.rglob("*.csv"):
        agenda_file = AGENDAS_DIR / f"{transcript_file.stem}.csv"

        if not agenda_file.exists():
            print(f"Agenda file not found for: {transcript_file.name}")
            continue

        print(f"Combining: {transcript_file.name}")
        combine_agenda_and_transcript(agenda_file, transcript_file)


if __name__ == "__main__":
    process_all_files()
