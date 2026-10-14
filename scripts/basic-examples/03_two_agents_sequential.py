"""
03 - Two agents passing work along (sequential process).

Researcher -> Writer. The writer's task gets the researcher's output
through `context=[...]`.
Run:  .venv\\Scripts\\python scripts\\basic-examples\\03_two_agents_sequential.py "electric cars"
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

researcher = Agent(
    role="Researcher",
    goal="Collect the key facts about {topic}",
    backstory="You are a careful analyst who lists facts, not opinions.",
    llm=llm,
)
writer = Agent(
    role="Blog Writer",
    goal="Turn research notes into an engaging short blog post",
    backstory="You write fun, easy-to-read posts for beginners.",
    llm=llm,
)

research_task = Task(
    description="List the 5 most important facts about {topic}.",
    expected_output="A numbered list of 5 facts, one sentence each.",
    agent=researcher,
)
write_task = Task(
    description="Write a short blog post about {topic} using the research notes.",
    expected_output="A blog post with a catchy title and about 150 words.",
    agent=writer,
    context=[research_task],  # <- receives the researcher's output
)

crew = Crew(
    agents=[researcher, writer],
    tasks=[research_task, write_task],  # run in this order
    process=Process.sequential,
)

topic = sys.argv[1] if len(sys.argv) > 1 else "electric cars"
result = crew.kickoff(inputs={"topic": topic})

# Every task's output is kept, not just the last one
print("\n===== RESEARCH NOTES (task 1) =====\n")
print(result.tasks_output[0].raw)
print("\n===== BLOG POST (task 2, final) =====\n")
print(result.raw)
