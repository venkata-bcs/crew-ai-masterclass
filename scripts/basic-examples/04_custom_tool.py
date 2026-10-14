"""
04 - Custom tools: give the agent "hands".

LLMs are bad at exact dates and arithmetic. Two small Python functions,
turned into tools with @tool, fix that. The docstring tells the LLM
when to use each tool.
Run:  .venv\\Scripts\\python scripts\\basic-examples\\04_custom_tool.py
"""

import os
import re
import sys
from datetime import date
from pathlib import Path

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
sys.stdout.reconfigure(encoding="utf-8")

from crewai import LLM, Agent, Crew, Task
from crewai.tools import tool

# --- LLM setup: read the NVIDIA key from settings.config (repo root) ---
SETTINGS = Path(__file__).resolve().parents[2] / "settings.config"
cfg = dict(re.findall(r"^[ \t]*(\w+)[ \t]*=[ \t]*['\"]?(.*?)['\"]?[ \t]*$", SETTINGS.read_text(encoding="utf-8"), re.M))
llm = LLM(
    model=cfg.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
    custom_openai=True,
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=cfg.get("NVIDIA_API_KEY") or cfg["NVDIA_API_KEY"],
)


@tool("Days until date")
def days_until(target_date: str) -> str:
    """Count how many days are left from today until a date. Input: date as YYYY-MM-DD."""
    days = (date.fromisoformat(target_date) - date.today()).days
    return f"Today is {date.today()}. There are {days} days until {target_date}."


@tool("Percentage calculator")
def percentage(value: float, percent: float) -> str:
    """Calculate a percentage of a number exactly, e.g. 18 percent of 2350."""
    return f"{percent}% of {value} = {value * percent / 100:.2f}"


assistant = Agent(
    role="Personal Assistant",
    goal="Answer questions accurately, always using tools for dates and maths",
    backstory="You never do arithmetic in your head; you always use a tool.",
    tools=[days_until, percentage],
    llm=llm,
    verbose=True,  # look for "Using Tool: ..." in the output
)

task = Task(
    description=(
        "I'm planning a trip on 2027-03-15 that costs 2350 dollars. "
        "How many days do I have left to save, and how much is an 18 percent deposit?"
    ),
    expected_output="Two short sentences: the days left and the deposit amount.",
    agent=assistant,
)

result = Crew(agents=[assistant], tasks=[task]).kickoff()
print("\n===== RESULT =====\n")
print(result.raw)
