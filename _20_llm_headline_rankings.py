# === Imports ===
import os
import csv
import time
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
from itertools import combinations
from trueskill import TrueSkill
import anthropic
from openai import OpenAI
import google.generativeai as genai

# === Load Environment Variables ===
load_dotenv()
claude_key = os.getenv("CLAUDE_KEY")
openai_key = os.getenv("OPENAI_KEY")
gemini_key = os.getenv("GEMINI_KEY")

# === Initialize Clients ===
claude_client = anthropic.Anthropic(api_key=claude_key)
openai_client = OpenAI(api_key=openai_key)
genai.configure(api_key=gemini_key)

# === Prompt Generator ===
def make_comparison_prompt(headline1, headline2):
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

---

### Examples

**Example 1**
Headline 1: City Council Approves $20 Million Affordable Housing Project  
Headline 2: Council Discusses Adding Public Art  
**More Important**: Headline 1

**Example 2**
Headline 1: City Declares 'Local History Month'  
Headline 2: Council Votes to Close Health Clinic Despite Protests  
**More Important**: Headline 2
"""

# === LLM Comparison Functions ===
def compare_headlines_claude(h1, h2):
    prompt = make_comparison_prompt(h1, h2)
    response = claude_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=64,
        temperature=0,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()

def compare_headlines_gemini(h1, h2):
    prompt = make_comparison_prompt(h1, h2)
    model = genai.GenerativeModel('gemini-2.5-pro')
    return model.generate_content(prompt).text.strip()

def compare_headlines_openai(h1, h2):
    prompt = make_comparison_prompt(h1, h2)
    response = openai_client.chat.completions.create(
        model="gpt-4.1-2025-04-14",
        messages=[{"role": "user", "content": prompt}],
        temperature=0,
        max_tokens=64
    )
    return response.choices[0].message.content.strip()

# === Configuration ===
WEEK = ("20250331", "20250404")
WEEK_STR = f"{WEEK[0]}_{WEEK[1]}"
GEN_LLM = "openai"   # options: "openai", "claude", "gemini"
RANK_LLM = "openai"

# === Load Headline Data ===
df = pd.read_csv(f"ranking_prep/{WEEK_STR}_filtered_headlines.csv")
claude_headlines = df["claude_headline"].tolist()
gemini_headlines = df["gemini_headline"].tolist()
openai_headlines = df["openai_headline"].tolist()

# === Map Headlines to Labels ===
headlines_by_model = {
    "claude": claude_headlines,
    "gemini": gemini_headlines,
    "openai": openai_headlines
}

labels_by_model = {
    "claude": [f"C{i}" for i in range(len(df))],
    "gemini": [f"G{i}" for i in range(len(df))],
    "openai": [f"O{i}" for i in range(len(df))]
}

headlines = headlines_by_model[GEN_LLM]
labels = labels_by_model[GEN_LLM]
headlines_to_labels = {h: l for h, l in zip(headlines, labels)}

# === Trueskill Environment ===
ts = TrueSkill(draw_probability=0)
ratings = {h: ts.create_rating() for h in headlines}

# === Run Pairwise Comparisons ===
pairs = list(combinations(headlines, 2))

for i, (h1, h2) in enumerate(pairs, 1):
    time.sleep(5)  # rate limiting

    # Choose LLM for ranking
    if RANK_LLM == "claude":
        winner = compare_headlines_claude(h1, h2)
    elif RANK_LLM == "gemini":
        winner = compare_headlines_gemini(h1, h2)
    else:
        winner = compare_headlines_openai(h1, h2)

    # Update ratings
    if winner == "Headline 1":
        ratings[h1], ratings[h2] = ts.rate_1vs1(ratings[h1], ratings[h2])
    elif winner == "Headline 2":
        ratings[h2], ratings[h1] = ts.rate_1vs1(ratings[h2], ratings[h1])
    else:
        raise ValueError(f"Unexpected output: {winner}")

    print(f"[{i}/{len(pairs)}] {headlines_to_labels[h1]} vs {headlines_to_labels[h2]} → {winner}")

# === Rank & Save Results ===
ranked = sorted(ratings.items(), key=lambda x: x[1].mu, reverse=True)
z = 1.96  # 95% confidence interval

results = []
print("\nFinal Rankings:")
for i, (headline, rating) in enumerate(ranked, 1):
    label = headlines_to_labels[headline]
    ci = z * rating.sigma
    print(f"{i}. {label} — {headline} (score: {rating.mu:.2f} ± {ci:.2f})")
    results.append({
        "rank": i,
        "label": label,
        "headline": headline,
        "score_mu": round(rating.mu, 2),
        "score_sigma": round(rating.sigma, 2),
        "score_95ci": round(ci, 2)
    })

# === Save to CSV ===
output_path = Path(f"rankings_by_llm/{WEEK_STR}_{GEN_LLM}_headlines_ranked_by_{RANK_LLM}.csv")
output_path.parent.mkdir(parents=True, exist_ok=True)

with open(output_path, "w", newline="", encoding="utf-8") as f:
    writer = csv.DictWriter(f, fieldnames=results[0].keys())
    writer.writeheader()
    writer.writerows(results)

print(f"\nResults saved to: {output_path}")
