"""
0.2 Words You Need to Know
Module 0 · Getting Started | Read first: md/00-getting-started/0_2_words_you_need_to_know.md

What you'll learn:
  Every glossary word (LLM, Agent, Tool, Task, Crew, Process, Kickoff, Result)
  pointed out in one tiny, working program. Look for the [WORD] tags.

Run (from the repo root):
  .venv\\Scripts\\python code\\00-getting-started\\0_2_glossary_in_code.py
"""

import os
import re
import sys
from pathlib import Path

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
sys.stdout.reconfigure(encoding="utf-8")

from crewai import LLM, Agent, Crew, Process, Task
from crewai.tools import tool

# [LLM] the "brain". Every agent thinks with one.
SETTINGS = Path(__file__).resolve().parents[2] / "settings.config"
cfg = dict(re.findall(r"^[ \t]*(\w+)[ \t]*=[ \t]*['\"]?(.*?)['\"]?[ \t]*$", SETTINGS.read_text(encoding="utf-8"), re.M))
llm = LLM(
    model=cfg.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
    custom_openai=True,
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=cfg.get("NVIDIA_API_KEY") or cfg["NVDIA_API_KEY"],
)


# [TOOL] something the agent can USE, not just think about.
@tool("Word counter")
def count_words(text: str) -> str:
    """Count the words in a piece of text."""
    return f"{len(text.split())} words"


# [AGENT] a worker with a role, a goal and a backstory.
poet = Agent(
    role="Haiku Poet",
    goal="Write a haiku about {subject} and verify its length",
    backstory="You write calm, simple haiku and always double-check your work.",
    tools=[count_words],
    llm=llm,
)

# [TASK] one piece of work, with a clear definition of "done".
write_haiku = Task(
    description="Write one haiku about {subject}. Use the word counter tool to check it.",
    expected_output="The haiku (3 lines), then its word count on a 4th line.",
    agent=poet,
)

# [CREW] the team: agents + tasks.   [PROCESS] the order they work in.
crew = Crew(agents=[poet], tasks=[write_haiku], process=Process.sequential)

# [KICKOFF] start the work. {subject} is filled in from inputs.
result = crew.kickoff(inputs={"subject": "morning coffee"})

# [RESULT] what comes back.
print("\n===== RESULT =====\n")
print(result.raw)

print("\n===== GLOSSARY MAP: what each word was in this program =====\n")
glossary = {
    "LLM": llm.model,
    "Agent": poet.role,
    "Tool": count_words.name,
    "Task": write_haiku.description[:50] + "...",
    "Crew": f"{len(crew.agents)} agent, {len(crew.tasks)} task",
    "Process": crew.process.value,
    "Kickoff": "crew.kickoff(inputs={'subject': 'morning coffee'})",
    "Result": f"result.raw ({len(result.raw)} characters)",
}
for word, value in glossary.items():
    print(f"  {word:<8} -> {value}")

# ---------------------------------------------------------------
# Takeaways
#   - Every CrewAI program uses the same handful of words.
#   - LLM thinks, Tool acts, Agent = LLM + identity + tools,
#     Task = the job, Crew = the team, Kickoff = "go".
