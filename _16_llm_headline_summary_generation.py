# === Imports ===
import os
import time
import pandas as pd
from pathlib import Path
from dotenv import load_dotenv
import anthropic
from openai import OpenAI
import google.generativeai as genai

# === Load environment variables ===
load_dotenv()
claude_key = os.getenv("CLAUDE_KEY")
openai_key = os.getenv("OPENAI_KEY")
gemini_key = os.getenv("GEMINI_KEY")

# === Initialize API clients ===
claude_client = anthropic.Anthropic(api_key=claude_key)
openai_client = OpenAI(api_key=openai_key)
genai.configure(api_key=gemini_key)

# === Prompt templates ===
def build_headline_prompt(text: str) -> str:
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
{text}
Headline:
"""

def build_summary_prompt(headline: str, combined_segment: str) -> str:
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

# === Headline generation ===
def generate_headline_claude(text):
    response = claude_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=64,
        temperature=0,
        messages=[{"role": "user", "content": build_headline_prompt(text)}]
    )
    return response.content[0].text.strip()

def generate_headline_gemini(text):
    model = genai.GenerativeModel("gemini-2.5-pro")
    return model.generate_content(build_headline_prompt(text)).text.strip()

def generate_headline_openai(text):
    response = openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": build_headline_prompt(text)}],
        temperature=0,
        max_tokens=64
    )
    return response.choices[0].message.content.strip()

# === Summary generation ===
def generate_summary_claude(headline, combined_segment):
    prompt = build_summary_prompt(headline, combined_segment)
    response = claude_client.messages.create(
        model="claude-sonnet-4-20250514",
        max_tokens=4096,
        temperature=0,
        messages=[{"role": "user", "content": prompt}]
    )
    return response.content[0].text.strip()

def generate_summary_gemini(headline, combined_segment):
    model = genai.GenerativeModel("gemini-2.5-pro")
    return model.generate_content(build_summary_prompt(headline, combined_segment)).text.strip()

def generate_summary_openai(headline, combined_segment):
    response = openai_client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[{"role": "user", "content": build_summary_prompt(headline, combined_segment)}],
        temperature=0,
        max_tokens=4096
    )
    return response.choices[0].message.content.strip()

# === LLM Loop ===
LLM_CODES = {"C": "claude", "G": "gemini", "O": "openai"}
BASE_DIR = Path("agenda_segments")

for llm_code, llm_name in LLM_CODES.items():
    for input_path in BASE_DIR.rglob("*.csv"):
        print(f"Processing ({llm_name}): {input_path.name}")

        output_path = Path(f"reports_{llm_name}") / f"{input_path.stem}.csv"
        output_path.parent.mkdir(parents=True, exist_ok=True)

        # Use output file if it exists (resume logic)
        active_path = output_path if output_path.exists() else input_path
        df = pd.read_csv(active_path)

        # Create columns if missing
        if f"{llm_name}_headline" not in df.columns:
            df[f"{llm_name}_headline"] = "NO_HEADLINE"
        if f"{llm_name}_summary" not in df.columns:
            df[f"{llm_name}_summary"] = "NO_SUMMARY"

        for idx, row in df.iterrows():
            combined_segment = row.get("manual_combined_segment", "")
            if combined_segment == "NO_SEGMENT":
                continue
            if row[f"{llm_name}_headline"] != "NO_HEADLINE":
                continue

            try:
                if llm_name == "claude":
                    headline = generate_headline_claude(combined_segment)
                    summary = generate_summary_claude(headline, combined_segment)
                    time.sleep(10)
                elif llm_name == "gemini":
                    headline = generate_headline_gemini(combined_segment)
                    summary = generate_summary_gemini(headline, combined_segment)
                    time.sleep(10)
                elif llm_name == "openai":
                    headline = generate_headline_openai(combined_segment)
                    summary = generate_summary_openai(headline, combined_segment)
                    time.sleep(10)

                df.at[idx, f"{llm_name}_headline"] = headline
                df.at[idx, f"{llm_name}_summary"] = summary

            except Exception as e:
                print(f"Error processing row {idx}: {e}")
                continue

        df.to_csv(output_path, index=False)
