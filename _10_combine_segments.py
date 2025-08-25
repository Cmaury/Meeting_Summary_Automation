import pandas as pd
from pathlib import Path
from datetime import datetime


def main():
    ######## CONFIGURATION ########
    INPUT_TRANSCRIPT_SEGMENTS_FOLDER = Path("transcript_segments")
    INPUT_AGENDA_SEGMENTS_FOLDER = Path("agenda_segments")
    START_DAY = datetime.strptime("20250519", "%Y%m%d")
    END_DAY = datetime.strptime("20250523", "%Y%m%d")
    ###############################

    combine_all_segments_in_folder(INPUT_TRANSCRIPT_SEGMENTS_FOLDER, INPUT_AGENDA_SEGMENTS_FOLDER, START_DAY, END_DAY)



def combine_all_segments_in_folder(transcript_segments_folder: Path, agenda_segments_folder: Path, start_day: datetime, end_day: datetime):
    """
    Pairs matching transcript segments for each agenda segment and combines agenda, legislation, and transcript into combined segment. Saves to original agenda segments location.

    Parameters:
    - transcript_segments_folder (Path): Path object of folder containing transcript segments.
    - agenda_segments_folder (Path): Path object of folder containing agenda segments and matched legislations. 
    - start_day (datetime): datetime object of earliest day in timeframe.
    - end_day (datetime): datetime object of latest day in timeframe. 
    """
    for agenda_file in sorted(agenda_segments_folder.rglob("*.csv")):
        meeting_date = str(agenda_file.name).split("_")[0]
        meeting_datetime = datetime.strptime(meeting_date, "%Y%m%d")

        # skip, out of time frame
        if not (start_day <= meeting_datetime <= end_day):
            continue

        print(f"combining: {agenda_file}")
        transcript_file = transcript_segments_folder / f"{agenda_file.name}"

        agenda_df = pd.read_csv(agenda_file)
        transcript_df = pd.read_csv(transcript_file)

        # default value
        agenda_df["matched_transcript"] = "NO_TRANSCRIPT"

        # special case where only one thing on agenda ("Public hearing", etc)
        if len(agenda_df) == 1 and len(transcript_df) == 1:
            agenda_df.loc[0, "matched_transcript"] = transcript_df.loc[0, "transcript"]
        else:
            # matches up transcript segments and agenda segments.
            for idx, row in transcript_df.iterrows():
                agenda_item = row["agenda_item"]
                transcript = row["transcript"]

                try:
                    agenda_num = int(agenda_item.split(":")[0].split(" ")[-1])
                except:
                    raise ValueError(f"!!! cannot find agenda item: {transcript_file}, row {str(idx)}")
                
                agenda_idx = agenda_num - 1

                if agenda_df.loc[agenda_idx, "matched_transcript"] == "NO_TRANSCRIPT":
                    agenda_df.loc[agenda_idx, "matched_transcript"] = transcript
                else:
                    agenda_df.loc[agenda_idx, "matched_transcript"] = agenda_df.loc[agenda_idx, "matched_transcript"] + " " + transcript
        
        

        # combining agenda, legislation, and transcript 
        agenda_df["combined_segment"] = "NO_SEGMENT"

        for idx, row in agenda_df.iterrows():
            agenda_segment = row["agenda_segment"]
            legislation = row["matched_legislation"]
            transcript_segment = row["matched_transcript"]

            # skip if there is no relevant transcript segments to the agenda segment, meaning not mentioned in transcript
            if transcript_segment == "NO_TRANSCRIPT":
                continue

            combined_segment = (
                "**Section of meeting agenda:**\n"
                f"{agenda_segment}\n\n"
                "**Section of meeting legislation:**\n"
                f"{legislation}\n\n"
                "**Section of meeting transcript:**\n"
                f"{transcript_segment}"
            )

            agenda_df.loc[idx, "combined_segment"] = combined_segment

        # save to original agenda segments file location
        agenda_df.to_csv(agenda_file, index=False)



if __name__ == "__main__":
    main()