"""
5.2 Out-of-the-box Tools
Module 5 · Tools | Read first: md/05-tools/5_2_out_of_the_box_tools.md

What you'll learn:
  Using ready-made tools from the `crewai-tools` package, no code needed:
    DirectoryReadTool  -> list files in a folder
    FileReadTool       -> read a file
    FileWriterTool     -> write a file
  The agent finds 3 meeting-note files, reads them, and writes a summary.

Setup:  pip install crewai-tools
Run (from the repo root):
  .venv\\Scripts\\python code\\05-tools\\5_2_out_of_the_box_tools.py
"""

import os
import re
import sys
from pathlib import Path

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
sys.stdout.reconfigure(encoding="utf-8")

from crewai import LLM, Agent, Crew, Task
from crewai.events import ToolUsageFinishedEvent, crewai_event_bus
from crewai_tools import DirectoryReadTool, FileReadTool, FileWriterTool

# --- LLM setup: read the NVIDIA key from settings.config (repo root) ---
SETTINGS = Path(__file__).resolve().parents[2] / "settings.config"
cfg = dict(re.findall(r"^[ \t]*(\w+)[ \t]*=[ \t]*['\"]?(.*?)['\"]?[ \t]*$", SETTINGS.read_text(encoding="utf-8"), re.M))
llm = LLM(
    model=cfg.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
    custom_openai=True,
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=cfg.get("NVIDIA_API_KEY") or cfg["NVDIA_API_KEY"],
)

# --- Create 3 small note files for the agent to work on ---
notes_dir = Path(__file__).parent / "output" / "meeting_notes"
notes_dir.mkdir(parents=True, exist_ok=True)
(notes_dir / "monday.txt").write_text("Monday: agreed to launch the mobile app on 1 March. Ana owns testing.", encoding="utf-8")
(notes_dir / "wednesday.txt").write_text("Wednesday: testing found 3 login bugs. Launch is at risk.", encoding="utf-8")
(notes_dir / "friday.txt").write_text("Friday: login bugs fixed. Launch stays on 1 March. Raj writes release notes.", encoding="utf-8")
summary_file = notes_dir.parent / "weekly_summary.md"

# --- Out-of-the-box tools: just create them ---
list_files = DirectoryReadTool(directory=str(notes_dir))  # locked to this folder
read_file = FileReadTool()  # reads any path the agent gives it
write_file = FileWriterTool()  # writes filename + content (+ optional directory)

# Log every tool call
calls = []


@crewai_event_bus.on(ToolUsageFinishedEvent)
def log_tool(source, event):
    calls.append(f"{event.tool_name}: {str(event.tool_args)[:70]}")


secretary = Agent(
    role="Team Secretary",
    goal="Turn a week of meeting notes into a short summary file",
    backstory="You read every note before writing anything.",
    tools=[list_files, read_file, write_file],
    llm=llm,
)

task = Task(
    description=(
        "1) List the files in the meeting notes folder. 2) Read every file. "
        f"3) Write a Markdown summary with sections 'Decisions', 'Risks' and 'Owners' "
        f"using the file writer: filename 'weekly_summary.md', directory '{summary_file.parent.as_posix()}', overwrite true."
    ),
    expected_output="Confirmation that weekly_summary.md was written, plus the summary text.",
    agent=secretary,
)

result = Crew(agents=[secretary], tasks=[task]).kickoff()

crewai_event_bus.flush()  # wait for CrewAI's events to be delivered

print("\n===== TOOL CALLS (in order) =====\n")
for i, call in enumerate(calls, 1):
    print(f"  {i}. {call}")

print(f"\n===== {summary_file.name} =====\n")
print(summary_file.read_text(encoding="utf-8") if summary_file.exists() else "(file was not written)")

# ---------------------------------------------------------------
# Takeaways
#   - crewai-tools has dozens of tools: files, web scraping, search, PDFs, databases.
#   - Configure a tool when you create it (e.g. lock DirectoryReadTool to one folder).
#   - Tools with side effects (writing files!) deserve a narrow scope.
