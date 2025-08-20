import os
import csv
import time
import json
from pathlib import Path
from datetime import datetime
from itertools import combinations
import pandas as pd
from dotenv import load_dotenv
from trueskill import TrueSkill
import anthropic
import random

def main():
    load_dotenv()

    ######## CONFIGURATION ########
    CLAUDE_KEY = os.getenv("CLAUDE_KEY")
    INPUT_REPORTS_FOLDER = Path("reports")
    OUTPUT_RANKINGS_FOLDER = Path("rankings")
    START_DAY = datetime.strptime("20250505", "%Y%m%d")
    END_DAY = datetime.strptime("20250509", "%Y%m%d")
    RANKING_MODEL = "claude-sonnet-4-20250514"
    RATE_LIMIT_SECONDS = 5
    ###############################

    claude_client = anthropic.Anthropic(api_key=CLAUDE_KEY)

    rank_headlines(
        INPUT_REPORTS_FOLDER,
        OUTPUT_RANKINGS_FOLDER,
        START_DAY,
        END_DAY,
        RANKING_MODEL,
        RATE_LIMIT_SECONDS,
        claude_client
    )



def make_comparison_prompt(headline1: str, headline2: str):
    return f"""
You will be shown two headlines from city council meetings.

### Your Task
Select the headline that is more important, using the definition below.

### What Does “Important” Mean?
A headline is important if:
- It reflects a major change to the status quo,
- OR it has a large impact on a large number of people,
- OR it has a large impact on a marginalized group (e.g., people facing poverty, discrimination, or limited access to resources),
- OR it covers an issue that is especially newsworthy due to its civic relevance, urgency, or long-term consequences.

### Consider These Factors
- **Scope**: How many people in the city are affected?
- **Depth**: How significant or lasting is the impact?
- **Equity**: Does it affect vulnerable or underserved communities?

---

### Compare the Headlines Below

Headline 1: {headline1}
Headline 2: {headline2}

---

Your output should be a single line: either `Headline 1` or `Headline 2` — no explanation.
"""


def compare_headlines_claude(h1: str, h2: str, ranking_model: str, client):
    """
    Prompts Claude to compare two headlines.

    Parameters:
    - h1 (str): string object containing first headline.
    - h2 (str): string object containing second headline.
    - ranking_model (str): string object of Claude model alias to compare (rank) headlines.
    - client: Claude API client. 
    """
    prompt = make_comparison_prompt(h1, h2)
    response = client.messages.create(
        model=ranking_model,
        max_tokens=64,
        temperature=0,
        messages=[{"role": "user", "content": prompt}],
    )
    return response.content[0].text.strip()


def collect_headlines_summaries(folder: Path, start_day: datetime, end_day: datetime):
    """
    Collects list of headline and parallel list of summaries in time frame.

    Parameters:
    - folder (Path): Path object of folder containing reports (headlines and summaries).
    - start_day (datetime): datetime object of earliest day in timeframe.
    - end_day (datetime): datetime object of latest day in timeframe.
    """
    headlines, summaries = [], []
    for reports_file in sorted(folder.rglob("*.csv")):
        meeting_date = str(reports_file.name).split("_")[0]
        meeting_datetime = datetime.strptime(meeting_date, "%Y%m%d")

        # skip, out of time frame
        if not (start_day <= meeting_datetime <= end_day):
            continue

        reports_df = pd.read_csv(reports_file)
        for _, row in reports_df.iterrows():
            # skip, default values
            if row["headline"] == "NO_HEADLINE" or row["summary"] == "NO_SUMMARY":
                continue

            # collect headline and summary
            headlines.append(row["headline"])
            summaries.append(row["summary"])
    return headlines, summaries


def build_label_maps(headlines, summaries):
    """
    Sets unique labels for each of the headlines and summaries.

    Parameters:
    - headlines: list of headlines.
    - summaries: list of parallel summaries.
    """
    headlines_to_labels = {}
    labels_to_headlines = {}
    labels_to_summaries = {}
    summaries_to_labels = {}

    for i in range(len(headlines)):
        # labels range from 1-N, where N is number of headlines
        label_h = f"H{i+1}"
        label_s = f"S{i+1}"

        labels_to_headlines[label_h] = headlines[i]
        headlines_to_labels[headlines[i]] = label_h

        labels_to_summaries[label_s] = summaries[i]
        summaries_to_labels[summaries[i]] = label_s

    return headlines_to_labels, labels_to_headlines, summaries_to_labels, labels_to_summaries


def save_label_maps_as_json(output_folder: Path,
                            headlines_to_labels, labels_to_headlines,
                            summaries_to_labels, labels_to_summaries,
                            start_day, end_day):
    """
    Saves label maps to single JSON in output folder.

    Parameters:
    - output_folder (Path): Path object of folder where labels maps will be saved.
    - headlines_to_labels: dictionary containing unique labels for each headline.
    - labels_to_headlines: dictionary containing headline for each label.
    - summaries_to_labels: dictionary containing unique labels for each headline.
    - labels_to_summaries: dictionary containing summary for each label.
    - start_day (datetime): datetime object of earliest day in timeframe.
    - end_day (datetime): datetime object of latest day in timeframe.
    """
    output_folder.mkdir(parents=True, exist_ok=True)
    json_path = output_folder / f'{start_day.strftime("%Y%m%d")}_{end_day.strftime("%Y%m%d")}_labels.json'

    # combine to one dictionary
    all_maps = {
        "headlines_to_labels": headlines_to_labels,
        "labels_to_headlines": labels_to_headlines,
        "summaries_to_labels": summaries_to_labels,
        "labels_to_summaries": labels_to_summaries
    }

    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(all_maps, f, ensure_ascii=False, indent=4)

    print(f"\nlabel maps saved: {json_path}")


def run_pairwise_comparisons(headlines, headlines_to_labels, ranking_model, rate_limit_seconds: int, client):
    """
    Prompts Claude to compare all pairwise comparisons of headlines to determine each headline's TrueSkill rating.

    Parameters:
    - headlines: list of headlines to rate.
    - headlines_to_labels: dictionary containing unique labels for each headline.
    - ranking_model (str): Claude model alias used to rank headlines.
    - rate_limit_seconds (int): number of seconds to wait between prompts.
    - client: Claude API client.
    """
    ts = TrueSkill(draw_probability=0)
    ratings = {h: ts.create_rating() for h in headlines}

    pairs = list(combinations(headlines, 2))

    for i, (h1, h2) in enumerate(pairs, 1):
        time.sleep(rate_limit_seconds)

        # randomly swap the order of h1 and h2 to reduce bias
        if random.choice([True, False]):
            h1, h2 = h2, h1

        winner = compare_headlines_claude(h1, h2, ranking_model, client)

        # adjust rating updates depending on whether we swapped
        if winner == "Headline 1":
            winner_h, loser_h = (h1, h2)
        elif winner == "Headline 2":
            winner_h, loser_h = (h2, h1)
        else:
            raise ValueError(f"!!! unexpected LLM output: {winner}")

        ratings[winner_h], ratings[loser_h] = ts.rate_1vs1(ratings[winner_h], ratings[loser_h])

        print(
            f"[{i}/{len(pairs)}] {headlines_to_labels[h1]} vs {headlines_to_labels[h2]} --- {headlines_to_labels[winner_h]}"
        )

    return ratings



def save_rankings(output_folder: Path, ratings, headlines_to_labels, start_day: datetime, end_day: datetime):
    """
    Calcualtes rankings from ratings of headlines based on pariwise comparisons and saves them to CSV file.

    Parameters:
    - output_folder (Path): Path object of folder where rankings will be saved. 
    - ratings: dictionary containing ratings of headlines based on pairwise comparisons.
    - headlines_to_labels: dictionary containing unique labels for each headline.
    - start_day (datetime): datetime object of earliest day in timeframe.
    - end_day (datetime): datetime object of latest day in timeframe.
    """
    ranked = sorted(ratings.items(), key=lambda x: x[1].mu, reverse=True)

    # 95% confidence interval
    z = 1.96

    results = []
    print("\nFinal Rankings:")
    for i, (headline, rating) in enumerate(ranked, 1):
        label = headlines_to_labels[headline]
        ci = z * rating.sigma
        print(f"{i}. {label} — {headline} (score: {rating.mu:.2f} ± {ci:.2f})")
        results.append(
            {
                "rank": i,
                "label": label,
                "headline": headline,
                "score_mu": round(rating.mu, 2),
                "score_sigma": round(rating.sigma, 2),
                "score_95ci": round(ci, 2),
            }
        )

    output_path = output_folder / f'{start_day.strftime("%Y%m%d")}_{end_day.strftime("%Y%m%d")}_ranking.csv'
    output_path.parent.mkdir(parents=True, exist_ok=True)

    with open(output_path, "w", newline="", encoding="utf-8") as f:
        writer = csv.DictWriter(f, fieldnames=results[0].keys())
        writer.writeheader()
        writer.writerows(results)

    print(f"\nresults saved to: {output_path}")




def rank_headlines(input_reports_folder: Path, output_rankings_folder: Path, start_day: datetime, end_day: datetime, ranking_model: str, rate_limit_seconds: int, claude_client):
    """
    Ranks headlines using pairwise comparisons and TrueSkill comparison model.

    Parameters:
    - input_reports_folder (Path): Path object of folder with reports (headlines and summaries).
    - output_rankings_folder (Path): Path object of folder where rankings and label maps are saved.
    - start_day (datetime): datetime object of earliest day in timeframe.
    - end_day (datetime): datetime object of latest day in timeframe.
    - ranking_model (str): string object of Claude model alias to rank headlines.
    - rate_limit_seconds (int): int object of number of seconds for Claude to sleep between prompts.
    - client: Claude API client.
    """
    
    headlines, summaries = collect_headlines_summaries(
        input_reports_folder, start_day, end_day
    )

    # map labels (H1, H2, …)
    (
        headlines_to_labels,
        labels_to_headlines,
        summaries_to_labels,
        labels_to_summaries,
    ) = build_label_maps(headlines, summaries)

    # save the label maps as JSON
    save_label_maps_as_json(
        output_rankings_folder,
        headlines_to_labels,
        labels_to_headlines,
        summaries_to_labels,
        labels_to_summaries,
        start_day,
        end_day,
    )

    # run pairwise comparisons
    ratings = run_pairwise_comparisons(
        headlines, headlines_to_labels, ranking_model, rate_limit_seconds, claude_client
    )

    # save results
    save_rankings(
         output_rankings_folder, ratings, headlines_to_labels, start_day, end_day
    )



if __name__ == "__main__":
    main()
