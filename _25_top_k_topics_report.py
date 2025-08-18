import pandas as pd
from pathlib import Path
import json

K = 3
WEEKS = [
    ("20250331", "20250404"),
    ("20250407", "20250411"),
    ("20250414", "20250418"),
    ("20250421", "20250425"),
]
LLMS = ["claude", "gemini", "openai"]

for week in WEEKS:
    for gen_llm in LLMS:
        for rank_llm in LLMS:

            # Read rankings CSV
            ranking_df = pd.read_csv(
                f"rankings_by_llm/{week[0]}_{week[1]}_{gen_llm}_headlines_ranked_by_{rank_llm}.csv"
            )

            if K > len(ranking_df):
                raise ValueError("K is greater than the number of available headlines.")

            # Get top K labels
            top_k_labels = list(ranking_df["label"])[:K]

            # Load labels mapping JSON
            labels_path = f"ranking_prep/{week[0]}_{week[1]}_labels.json"
            with open(labels_path, "r", encoding="utf-8") as f:
                labels_dict = json.load(f)

            labels_to_headlines = labels_dict["labels_to_headlines"]
            labels_to_summaries = labels_dict["labels_to_summaries"]

            # Collect top K headlines and summaries
            top_k_headlines = []
            top_k_summaries = []

            for label in top_k_labels:
                top_k_headlines.append(labels_to_headlines[label])
                top_k_summaries.append(labels_to_summaries[label])

            # Prepare output text
            output_lines = []
            for i in range(K):
                output_lines.append(f"Headline {i+1}: {top_k_headlines[i]}")
                output_lines.append(f"Summary {i+1}: {top_k_summaries[i]}")
                output_lines.append("")  # Blank line between entries

            output_text = "\n".join(output_lines)

            # Save to TXT file
            output_dir = Path("_final_outputs")
            output_dir.mkdir(exist_ok=True)
            output_path = output_dir / f"{week[0]}_{week[1]}_top_{K}_{gen_llm}_ranked_by_{rank_llm}.txt"

            with open(output_path, "w", encoding="utf-8") as f:
                f.write(output_text)

            print(f"Top {K} headlines and summaries saved to: {output_path}")
