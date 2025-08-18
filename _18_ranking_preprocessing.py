import pandas as pd
import json
import random
from pathlib import Path
from datetime import datetime

# ========== Config & Setup ==========

WEEK = ("20250421", "20250425")
START_DATE = datetime.strptime(WEEK[0], "%Y%m%d")
END_DATE = datetime.strptime(WEEK[1], "%Y%m%d")

LLM_MAP = {"C": "claude", "G": "gemini", "O": "openai"}

# ========== Load Headlines & Summaries ==========

claude_headlines, gemini_headlines, openai_headlines, manual_headlines = [], [], [], []
claude_summaries, gemini_summaries, openai_summaries, manual_summaries = [], [], [], []

for llm_code in LLM_MAP:
    llm_name = LLM_MAP[llm_code]
    report_dir = Path(f"reports_{llm_name}")

    for file in sorted(report_dir.rglob("*.csv")):
        date_str = str(file.stem).split("_")[0]
        meeting_date = datetime.strptime(date_str, "%Y%m%d")

        if not (START_DATE <= meeting_date <= END_DATE):
            continue

        df = pd.read_csv(file)
        for _, row in df.iterrows():
            if row[f"{llm_name}_headline"] == "NO_HEADLINE" or row[f"{llm_name}_summary"] == "NO_SUMMARY":
                continue

            if llm_code == "C":
                claude_headlines.append(row["claude_headline"])
                claude_summaries.append(row["claude_summary"])
                manual_headlines.append(row["true_headline"])
                manual_summaries.append(row["true_summary"])
            elif llm_code == "G":
                gemini_headlines.append(row["gemini_headline"])
                gemini_summaries.append(row["gemini_summary"])
            elif llm_code == "O":
                openai_headlines.append(row["openai_headline"])
                openai_summaries.append(row["openai_summary"])

# ========== Manual Skips ==========

skip_flags = []
skipped_count = 0

print(len(claude_headlines))
for headline in claude_headlines:
    inp = input(headline + ": ")
    if inp.strip().lower() == "s":
        skip_flags.append(1)
        skipped_count += 1
    else:
        skip_flags.append(0)

print(f"Total skipped: {skipped_count}")


# ========== Save & Filter Skipped Headlines ==========
print(len(manual_headlines))
print(len(claude_headlines))
print(len(gemini_headlines))
print(len(openai_headlines))
print(len(skip_flags))
print(len(manual_headlines))


evaluation_path = f"ranking_prep/{WEEK[0]}_{WEEK[1]}"
Path("ranking_prep").mkdir(exist_ok=True)

df = pd.DataFrame({
    "manual_headline": manual_headlines,
    "claude_headline": claude_headlines,
    "gemini_headline": gemini_headlines,
    "openai_headline": openai_headlines,
    "skip": skip_flags,
    "manual_summary": manual_summaries,
    "claude_summary": claude_summaries,
    "gemini_summary": gemini_summaries,
    "openai_summary": openai_summaries,
})

df.to_csv(f"{evaluation_path}_headlines.csv", index=False)

df = df[df["skip"] != 1].drop("skip", axis=1)
df.to_csv(f"{evaluation_path}_filtered_headlines.csv", index=False)

# ========== Create Pairwise Questions ==========

df = pd.read_csv(f"{evaluation_path}_filtered_headlines.csv")
questions_df = pd.DataFrame(columns=["Headline 1", "Headline 2"])

def add_pairwise_question(h1, h2, label1=None, label2=None):
    flip = random.randint(0, 1)
    row = {
        "Headline 1": h1 if flip == 0 else h2,
        "Headline 2": h2 if flip == 0 else h1,
    }
    if label1 and label2:
        row["label1"] = label1 if flip == 0 else label2
        row["label2"] = label2 if flip == 0 else label1
    questions_df.loc[len(questions_df)] = row

# Intra-model pairwise (Claude/Gemini/OpenAI)
for i in range(len(df)):
    for j in range(i + 1, len(df)):
        for model in ["claude_headline", "gemini_headline", "openai_headline"]:
            add_pairwise_question(df.iloc[i][model], df.iloc[j][model])

# Manual vs. LLM pairs
for i, row in df.iterrows():
    manual = row["manual_headline"]
    if manual == "NO_HEADLINE":
        continue
    for j, other in df.iterrows():
        if i == j:
            continue
        for model in ["claude_headline", "gemini_headline", "openai_headline"]:
            add_pairwise_question(manual, other[model])

# Manual vs. Manual (labelled)
for i in range(len(df)):
    for j in range(i + 1, len(df)):
        m1, m2 = df.iloc[i]["manual_headline"], df.iloc[j]["manual_headline"]
        if m1 == "NO_HEADLINE" or m2 == "NO_HEADLINE":
            continue
        add_pairwise_question(m1, m2, label1=f"M{i}", label2=f"M{j}")

# ========== Save Pairwise Questions ==========

questions_df.to_csv(f"{evaluation_path}_questions.csv", index=False)
print(f"Total question pairs generated: {len(questions_df)}")

# ========== Label Mapping ==========

headlines_to_labels = {}
labels_to_headlines = {}
labels_to_summaries = {}
summaries_to_labels = {}

for idx, row in df.iterrows():
    for prefix, headline in zip(["M", "C", "G", "O"], [
        row["manual_headline"], row["claude_headline"],
        row["gemini_headline"], row["openai_headline"]
    ]):
        if headline == "NO_HEADLINE" and prefix == "M":
            continue
        label = f"{prefix}{idx}"
        headlines_to_labels[headline] = label
        labels_to_headlines[label] = headline

for idx, row in df.iterrows():
    for prefix, summary in zip(["M", "C", "G", "O"], [
        row["manual_summary"], row["claude_summary"],
        row["gemini_summary"], row["openai_summary"]
    ]):
        if summary == "NO_SUMMARY" and prefix == "M":
            continue
        label = f"{prefix}{idx}"
        summaries_to_labels[summary] = label
        labels_to_summaries[label] = summary

with open(f"{evaluation_path}_labels.json", "w") as f:
    json.dump({
        "headlines_to_labels": headlines_to_labels,
        "labels_to_headlines": labels_to_headlines,
        "summaries_to_labels": summaries_to_labels,
        "labels_to_summaries": labels_to_summaries
    }, f)
