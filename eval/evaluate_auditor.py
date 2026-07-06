import os
import logging
import warnings

# Completely disable OpenTelemetry globally before anything else loads
os.environ["OTEL_SDK_DISABLED"] = "true"

# Suppress standard Python warnings early before imports trigger them
warnings.filterwarnings("ignore")

from vertexai import init  # noqa: E402
from vertexai.generative_models import GenerativeModel  # noqa: E402
from dotenv import load_dotenv  # noqa: E402

# Load env variables explicitly
load_dotenv(dotenv_path=".env")
GCP_PROJECT_ID = os.getenv("GOOGLE_CLOUD_PROJECT")
REGION = os.getenv("GOOGLE_CLOUD_LOCATION")

# Force-suppress absolutely ALL INFO and WARNING logs globally
logging.disable(logging.WARNING)


def read_txt(file_path: str) -> str:
    try:
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    except Exception as e:
        print(f"Error reading {file_path}: {e}")
        return ""


def evaluate_with_gemini_judge(reports: dict) -> str:
    """
    Evaluate the Auditor agent's reports using Gemini Flash LLM-as-a-Judge.
    """
    if not GCP_PROJECT_ID or not REGION:
        print(
            "Skipping evaluation: GOOGLE_CLOUD_PROJECT or GOOGLE_CLOUD_LOCATION environment variable not set.",
        )
        return ""

    init(project=GCP_PROJECT_ID, location=REGION)
    gemini_model = GenerativeModel("gemini-2.5-flash")

    base_prompt = """
    You are an expert Data Quality Assessor grading an autonomous AI Auditor Agent.

    You must evaluate the agent's data quality audit reports against a known Ground Truth of injected errors.

    Goal: Assess if the agent successfully identified the specific error classes we injected and summarize its performance.

    ---
    **Ground Truth Errors Injected:**

    **Structural Errors (4):**
    1. Missing Values (Nulls)
    2. Duplicate Rows
    3. Outliers (Extreme max values)
    4. Categorical Errors (Random alphanumeric strings)

    **Logical Errors (7):**
    1. Clicks > Impressions
    2. Conversions > Clicks
    3. Spend > 0 while Impressions = 0
    4. Video Completions > Plays
    5. Purchases without Add to Cart
    6. Landing Page Views > Clicks
    7. Negative Metric Values
    ---

    **Auditor Agent's Final Reports:**
    """

    for filename, report_text in reports.items():
        base_prompt += f"\n    [REPORT: {filename}]\n    {report_text}\n"

    base_prompt += """
    ---

    Please write a comprehensive evaluation scorecard in plain text format (do not use .md file blocks).
    Use headers, bullet points, and checkmarks (✅/❌) to indicate if the agent successfully detected each error from the Ground Truth injected list above for EACH report.

    Structure your evaluation identically to this format:

    Auditor Agent Evaluation Scorecard
    ================================

    Report: [Filename]
    ----------------
    Structural Errors: X / 4
    * [List ALL 4 structural errors and whether it found them, explaining briefly what it found or missed]

    Logical Errors: Y / 7
    * [List ALL 7 logical errors and whether it found them]

    Summary: [A brief one-paragraph summary of the agent's performance, what it did well, and what it completely missed.]

    Report: [Next Filename]
    ----------------
    ...
    """

    print(
        f"\n🧠 Using Gemini Flash Judge to formulate the scorecard for {len(reports)} reports...",
    )

    try:
        response = gemini_model.generate_content(base_prompt)
        return response.text.strip()
    except Exception as e:
        print(f"❌ Error during Gemini evaluation: {e}")
        return ""


def main():
    print("--- Starting Auditor Agent Evaluation ---")

    script_dir = os.path.dirname(os.path.abspath(__file__))

    # Place the paths to the response files here
    filepaths = [
        os.path.join(script_dir, "auditor_response.txt"),
    ]

    reports = {}
    for fp in filepaths:
        print(f"Reading {fp}...")
        report_text = read_txt(fp)
        if report_text:
            reports[os.path.basename(fp)] = report_text

    if not reports:
        print("⚠️ Warning: Could not find or read any .txt response files. Aborting.")
        return

    # Generate Evaluation
    evaluation_result = evaluate_with_gemini_judge(reports)

    if evaluation_result:
        output_file = os.path.join(script_dir, "evaluation_scorecard.txt")
        print(f"\n💾 Saving evaluation scorecard to {output_file}...")
        with open(output_file, "w", encoding="utf-8") as f:
            f.write(evaluation_result)
            f.write("\n")
        print("✅ Results saved locally!")
        print("\n" + "=" * 40 + "\n")
        print(evaluation_result)


if __name__ == "__main__":
    main()
