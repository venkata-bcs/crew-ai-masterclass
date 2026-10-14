"""
2.2 Newsletter Pipeline Example
Module 2 · Thinking in Multi-Agent Systems | Read first: md/02-multi-agent-thinking/2_2_newsletter_pipeline.md

What you'll learn:
  How to design a real multi-agent pipeline:
    Researcher -> Writer -> Editor  ->  newsletter_<topic>.md
  Each agent has ONE job. Each task says exactly what it hands on.

Run (from the repo root):
  .venv\\Scripts\\python code\\02-multi-agent-thinking\\2_2_newsletter_pipeline.py "Python tips"
"""

import os
import re
import sys
from pathlib import Path

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
sys.stdout.reconfigure(encoding="utf-8")

from crewai import LLM, Agent, Crew, Process, Task

# --- LLM setup: read the NVIDIA key from settings.config (repo root) ---
SETTINGS = Path(__file__).resolve().parents[2] / "settings.config"
cfg = dict(re.findall(r"^[ \t]*(\w+)[ \t]*=[ \t]*['\"]?(.*?)['\"]?[ \t]*$", SETTINGS.read_text(encoding="utf-8"), re.M))
llm = LLM(
    model=cfg.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
    custom_openai=True,
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=cfg.get("NVIDIA_API_KEY") or cfg["NVDIA_API_KEY"],
)

topic = sys.argv[1] if len(sys.argv) > 1 else "Python tips"
output_file = Path(__file__).parent / "output" / f"newsletter_{re.sub(r'[^a-z0-9]+', '_', topic.lower()).strip('_')}.md"

# --- The team: one job each ---
researcher = Agent(
    role="Newsletter Researcher",
    goal="Find 3 useful, accurate ideas about {topic} for beginners",
    backstory="You pick ideas readers can use today, and explain why each matters.",
    llm=llm,
)
writer = Agent(
    role="Newsletter Writer",
    goal="Turn research notes into a friendly, scannable newsletter",
    backstory="You write short paragraphs, clear headings and a warm tone.",
    llm=llm,
)
editor = Agent(
    role="Newsletter Editor",
    goal="Make the newsletter correct, consistent and ready to send",
    backstory="You fix errors, trim waffle and keep the format exactly right.",
    llm=llm,
)

# --- The handoffs: what each step produces for the next ---
research = Task(
    description="Research {topic}. Pick 3 ideas a beginner can use this week.",
    expected_output="3 ideas, each with: a title, a 2-sentence explanation, and one tiny example.",
    agent=researcher,
)
write = Task(
    description="Write this week's newsletter about {topic} using the research notes.",
    expected_output=(
        "Markdown: a # title, a 1-line intro, one ## section per idea, "
        "and a closing 'Try this week' line."
    ),
    agent=writer,
    context=[research],  # gets the researcher's notes
)
edit = Task(
    description="Edit the newsletter: fix mistakes, keep it under 300 words, keep the Markdown format.",
    expected_output="The final newsletter in raw Markdown (no ``` fences).",
    agent=editor,
    context=[write],  # gets the writer's draft
    output_file=str(output_file),  # CrewAI saves the final answer here
)

crew = Crew(agents=[researcher, writer, editor], tasks=[research, write, edit], process=Process.sequential)
result = crew.kickoff(inputs={"topic": topic})

print("\n===== WHAT EACH STEP HANDED ON =====")
for task_output in result.tasks_output:
    print(f"\n--- {task_output.agent} ({len(task_output.raw.split())} words) ---")
    print(task_output.raw[:400] + ("..." if len(task_output.raw) > 400 else ""))

print(f"\n===== SAVED: {output_file} =====")

# ---------------------------------------------------------------
# Takeaways
#   - Design the pipeline first: who does what, what passes between them.
#   - expected_output is the "contract" for each handoff.
#   - result.tasks_output lets you inspect every step, not just the end.
