import pandas as pd
from pathlib import Path
from datetime import datetime
import json


def main():
    ######## CONFIGURATION ########
    K = 3
    OUTPUT_FOLDER = Path("_final_outputs")
    START_DAY = datetime.strptime("20250512", "%Y%m%d")
    END_DAY = datetime.strptime("20250516", "%Y%m%d")
    ###############################

    save_top_k_headlines_and_summaries(K, OUTPUT_FOLDER, START_DAY, END_DAY)


def save_top_k_headlines_and_summaries(k: int, output_folder: Path, start_day: datetime, end_day: datetime):
    """
    Extracts top-k headlines and summaries from ranking and label files and saves them to a TXT file.

    Parameters:
    - k (int): int object of number of headlines and summaries to include in article. 
    - output_folder (Path): Path object of folder where final TXT article will be saved.
    - start_day (datetime): datetime object of earliest day in timeframe.
    - end_day (datetime): datetime object of latest day in timeframe. 
    """
    # ranking CSV
    ranking_file = f'rankings/{start_day.strftime("%Y%m%d")}_{end_day.strftime("%Y%m%d")}_ranking.csv'
    ranking_df = pd.read_csv(ranking_file)

    if k > len(ranking_df):
        raise ValueError("K more than number of headlines")

    # get top-k label indices (e.g. H17 -> 17)
    top_k_labels = [x[1:] for x in list(ranking_df["label"])[:k]]

    # load labels mapping JSON
    labels_file = f'rankings/{start_day.strftime("%Y%m%d")}_{end_day.strftime("%Y%m%d")}_labels.json'
    with open(labels_file, "r", encoding="utf-8") as f:
        labels_dict = json.load(f)

    labels_to_headlines = labels_dict["labels_to_headlines"]
    labels_to_summaries = labels_dict["labels_to_summaries"]

    # collect top-k headlines and summaries
    top_k_headlines = [labels_to_headlines["H" + label] for label in top_k_labels]
    top_k_summaries = [labels_to_summaries["S" + label] for label in top_k_labels]

    # format output text
    output_lines = []
    for i in range(k):
        output_lines.append(f"Headline {i+1}: {top_k_headlines[i]}")
        output_lines.append(f"Summary {i+1}: {top_k_summaries[i]}")
        output_lines.append("")

    output_text = "\n".join(output_lines)

    # save to TXT file
    output_folder.mkdir(exist_ok=True)
    output_path = output_folder / f'{start_day.strftime("%Y%m%d")}_{end_day.strftime("%Y%m%d")}_final_{k}.txt'
    with open(output_path, "w", encoding="utf-8") as f:
        f.write(output_text)

    print(f"top {k} headlines and summaries saved: {output_path}")


if __name__ == "__main__":
    main()
