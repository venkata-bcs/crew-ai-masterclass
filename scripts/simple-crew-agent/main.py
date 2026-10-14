"""
Start button: builds the crew and runs it for one country.

Usage (from the repo root):
    .venv\\Scripts\\python scripts\\simple-crew-agent\\main.py Japan
    .venv\\Scripts\\python scripts\\simple-crew-agent\\main.py "New Zealand"

Output: scripts/simple-crew-agent/output/<country>.md
"""

import argparse
import os
import re
import sys
from pathlib import Path

# Turn off CrewAI telemetry before crewai is imported (same as common/config.py).
os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
# CrewAI prints emoji; the default Windows console encoding can't, so force UTF-8.
sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")

from crewai import Crew, Process

from agent import create_country_researcher
from llm import create_llm
from tasks import create_country_report_task

OUTPUT_DIR = Path(__file__).resolve().parent / "output"


def strip_code_fences(markdown: str) -> str:
    """Some LLMs wrap their answer in ```markdown ... ``` despite being asked not to."""
    match = re.fullmatch(r"\s*```(?:markdown|md)?\s*\n(.*?)\n```\s*", markdown, flags=re.DOTALL)
    return match.group(1) if match else markdown


def main() -> None:
    parser = argparse.ArgumentParser(description="Research a country and write a Markdown fact sheet.")
    parser.add_argument("country", help="Country name, e.g. Japan")
    args = parser.parse_args()

    country = args.country.strip()
    output_file = OUTPUT_DIR / f"{re.sub(r'[^A-Za-z0-9]+', '_', country).strip('_').lower()}.md"

    researcher = create_country_researcher(create_llm())
    report_task = create_country_report_task(researcher, output_file)

    crew = Crew(
        agents=[researcher],
        tasks=[report_task],
        process=Process.sequential,
    )
    result = crew.kickoff(inputs={"country": country})

    output_file.write_text(strip_code_fences(result.raw).strip() + "\n", encoding="utf-8")
    print(f"\nSaved: {output_file}")


if __name__ == "__main__":
    main()
