"""
5.3 Third-party Tools
Module 5 · Tools | Read first: md/05-tools/5_3_third_party_tools.md

What you'll learn:
  Two ways to use tools that were NOT written for CrewAI:
    A) LangChain tools  -> wrap them in a tiny @tool function
    B) MCP servers      -> connect with mcps=[...]; CrewAI discovers the tools
  For B, this same file also acts as a tiny MCP server (run with --serve),
  so the demo needs nothing else. In real life you'd point at any MCP server.

Setup:  pip install langchain-community wikipedia
Run (from the repo root):
  .venv\\Scripts\\python code\\05-tools\\5_3_third_party_tools.py
"""

import os
import re
import sys
import warnings
from pathlib import Path

warnings.filterwarnings("ignore", category=DeprecationWarning)

# ---------------------------------------------------------------
# Part B's server side. When started with --serve, this file is an
# MCP server exposing one tool over stdin/stdout, and nothing else.
# ---------------------------------------------------------------
if "--serve" in sys.argv:
    warnings.filterwarnings("ignore")  # keep the server quiet
    from mcp.server.fastmcp import FastMCP

    server = FastMCP("text-stats", log_level="WARNING")

    @server.tool()
    def text_stats(text: str) -> str:
        """Count words, sentences and characters in a text."""
        sentences = len([s for s in re.split(r"[.!?]+", text) if s.strip()])
        return f"{len(text.split())} words, {sentences} sentences, {len(text)} characters"

    server.run()  # speaks MCP over stdio until the client disconnects
    sys.exit()

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
sys.stdout.reconfigure(encoding="utf-8")

from crewai import LLM, Agent, Crew, Task
from crewai.events import ToolUsageFinishedEvent, crewai_event_bus
from crewai.mcp import MCPServerStdio
from crewai.tools import tool
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

# ---------------------------------------------------------------
# A) LangChain tool -> CrewAI tool (a 3-line wrapper)
#    Passing the LangChain object straight to tools=[...] fails validation.
# ---------------------------------------------------------------
langchain_wikipedia = WikipediaQueryRun(api_wrapper=WikipediaAPIWrapper(top_k_results=1, doc_content_chars_max=800))


@tool("Wikipedia")
def wikipedia(query: str) -> str:
    """Look up a person or topic on Wikipedia."""
    return langchain_wikipedia.run(query)


# ---------------------------------------------------------------
# B) MCP server: describe HOW to start it; CrewAI connects and
#    lists its tools automatically. Here: this file with --serve.
# ---------------------------------------------------------------
text_stats_server = MCPServerStdio(command=sys.executable, args=[str(Path(__file__).resolve()), "--serve"])

calls = []


@crewai_event_bus.on(ToolUsageFinishedEvent)
def log_tool(source, event):
    calls.append(event.tool_name)


biographer = Agent(
    role="Biographer",
    goal="Write accurate mini-biographies and report their length",
    backstory="You check facts on Wikipedia and measure your text with the text stats tool.",
    tools=[wikipedia],  # A) wrapped LangChain tool
    mcps=[text_stats_server],  # B) every tool on the MCP server
    llm=llm,
)

task = Task(
    description="Look up {person} on Wikipedia, write a 3-sentence biography, then get its text stats.",
    expected_output="The 3-sentence biography, then a line 'Stats: ...'.",
    agent=biographer,
)

result = Crew(agents=[biographer], tasks=[task]).kickoff(inputs={"person": "Ada Lovelace"})

crewai_event_bus.flush()  # wait for CrewAI's events to be delivered

print("\n===== RESULT =====\n")
print(result.raw)
print("\n===== TOOLS USED =====\n")
for name in dict.fromkeys(calls):
    # MCP tools get a long server prefix in their name, so label them by source
    source = "LangChain (wrapped)" if name.lower() == wikipedia.name.lower() else "MCP server (text_stats)"
    print(f"  {source:<26} {calls.count(name)}x")

# ---------------------------------------------------------------
# Takeaways
#   - LangChain tools: wrap with @tool (or a BaseTool) and you're done.
#   - MCP (Model Context Protocol) is the universal plug for tools:
#     GitHub, Slack, databases, browsers... thousands of servers exist.
#   - MCPServerStdio = start a local server; MCPServerHTTP = connect to a URL.
