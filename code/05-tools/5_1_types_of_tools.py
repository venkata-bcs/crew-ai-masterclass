"""
5.1 Types of Tools
Module 5 · Tools | Read first: md/05-tools/5_1_types_of_tools.md

What you'll learn:
  The 3 families of tools, all on ONE agent:
    📦 out-of-the-box  FileReadTool          (from the crewai-tools package)
    🔌 third-party     Wikipedia             (a LangChain tool, wrapped)
    🧑‍💻 custom          Word counter          (your own @tool function)
  And the difference between AGENT-level tools (always available)
  and TASK-level tools (only for that task, overriding the agent's).

Run (from the repo root):
  .venv\\Scripts\\python code\\05-tools\\5_1_types_of_tools.py
"""

import os
import re
import sys
import warnings
from pathlib import Path

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
sys.stdout.reconfigure(encoding="utf-8")
warnings.filterwarnings("ignore", category=DeprecationWarning)

from crewai import LLM, Agent, Crew, Task
from crewai.events import ToolUsageFinishedEvent, crewai_event_bus
from crewai.tools import tool
from crewai_tools import FileReadTool
from langchain_community.tools import WikipediaQueryRun
from langchain_community.utilities import WikipediaAPIWrapper

# --- LLM setup: read the NVIDIA key from settings.config (repo root) ---
SETTINGS = Path(__file__).resolve().parents[2] / "settings.config"
cfg = dict(re.findall(r"^[ \t]*(\w+)[ \t]*=[ \t]*['\"]?(.*?)['\"]?[ \t]*$", SETTINGS.read_text(encoding="utf-8"), re.M))
llm = LLM(
    model=cfg.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
    custom_openai=True,
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=cfg.get("NVIDIA_API_KEY") or cfg["NVDIA_API_KEY"],
)

# A small file for the out-of-the-box tool to read
notes = Path(__file__).parent / "output" / "notes.txt"
notes.parent.mkdir(exist_ok=True)
notes.write_text("Meeting notes: we decided to build our next prototype with the Rust programming language.\n", encoding="utf-8")

# 📦 Family 1: out-of-the-box. Import, configure, done.
file_reader = FileReadTool(file_path=str(notes))

# 🔌 Family 2: third-party. LangChain tools are not CrewAI tools,
#    so we wrap one inside a small @tool function.
wikipedia = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper(top_k_results=1, doc_content_chars_max=600))


@tool("Wikipedia")
def wikipedia_search(query: str) -> str:
    """Look up a topic on Wikipedia and return a short summary."""
    return wikipedia.run(query)


# 🧑‍💻 Family 3: custom. Any Python function you like.
@tool("Word counter")
def count_words(text: str) -> str:
    """Count the words in a piece of text."""
    return f"{len(text.split())} words"


# Log which tool was used, by which agent
used = []


def simple(name: str) -> str:
    """Events report a tidied tool name ('read_a_files_content'), so compare letters only."""
    return re.sub(r"[^a-z0-9]", "", name.lower())


@crewai_event_bus.on(ToolUsageFinishedEvent)
def log_tool(source, event):
    used.append(simple(event.tool_name))


researcher = Agent(
    role="Researcher",
    goal="Combine company notes with public facts",
    backstory="You always read the notes first, then check facts.",
    tools=[file_reader, wikipedia_search],  # AGENT-level: available for every task
    llm=llm,
)

summarise = Task(
    description="Read the meeting notes, find which programming language was chosen, look it up on Wikipedia, and summarise both in 3 sentences.",
    expected_output="3 sentences: the decision, and 2 facts about the language.",
    agent=researcher,
)
measure = Task(
    description="Count the words of your 3-sentence summary with the word counter.",
    expected_output="The word count.",
    agent=researcher,
    context=[summarise],
    tools=[count_words],  # TASK-level: replaces the agent's tools for this task only
)

result = Crew(agents=[researcher], tasks=[summarise, measure]).kickoff()

crewai_event_bus.flush()  # wait for CrewAI's events to be delivered

print("\n===== SUMMARY =====\n" + result.tasks_output[0].raw.strip())
print("\n===== WORD COUNT =====\n" + result.raw.strip())

print("\n===== TOOL FAMILIES =====\n")
family = {file_reader.name: "📦 out-of-the-box", wikipedia_search.name: "🔌 third-party", count_words.name: "🧑‍💻 custom"}
for name, kind in family.items():
    print(f"  {kind:<20} {name:<28} used {used.count(simple(name))}x")

# ---------------------------------------------------------------
# Takeaways
#   - Out-of-the-box: fastest to use. Third-party: huge ecosystem, may need
#     a wrapper. Custom: anything Python can do.
#   - Agent-level tools = the agent's toolbox. Task-level tools = a special
#     toolbox for one task (it REPLACES the agent's tools for that task).
