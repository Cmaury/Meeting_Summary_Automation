import pandas as pd
from pathlib import Path

def main():
    ######## CONFIGURATION ########
    AGENDA_SEGMENTS_FOLDER = Path("agenda_segments")
    LEGISLATION_FOLDER = Path("legislations")
    ###############################

    match_legislation_to_agenda_segments(AGENDA_SEGMENTS_FOLDER, LEGISLATION_FOLDER)



def match_legislation_to_agenda_segments(agenda_segments_folder: Path, legislations_folder: Path):
    """
    Iterates through agenda segments to match corresponding legislation texts.

    Parameters:
    - agenda_segments_folder (Path): Path object containing CSV files containing segmented agenda texts.
    - legislations_folder (Path): Path object containing CSV files containing legislations texts.
    """

    for leg_file in legislations_folder.rglob("*.csv"):
        print(f"matching: {leg_file}")
        aseg_file = agenda_segments_folder / leg_file.name
        
        # read CSV files
        aseg_df = pd.read_csv(aseg_file)
        leg_df = pd.read_csv(leg_file)

        # default value
        aseg_df["matched_legislation"] = "NO_LEGISLATION"

        # find matches
        for _, leg_row in leg_df.iterrows():
            for aseg_idx, aseg_row in aseg_df.iterrows():
                if leg_row["item"] in aseg_row["agenda_segment"]:
                    # set to legislation text if default value and append if already been changed
                    if aseg_df.at[aseg_idx, "matched_legislation"] == "NO_LEGISLATION":
                        aseg_df.at[aseg_idx,"matched_legislation"] = leg_row["text"]
                    else:
                        aseg_df.at[aseg_idx,"matched_legislation"] = aseg_df.at[aseg_idx,"matched_legislation"] + leg_row["text"]
            

        aseg_df.to_csv(aseg_file,index=False)



if __name__ == "__main__":
    main()