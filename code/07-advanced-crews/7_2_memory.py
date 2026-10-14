"""
7.2 Memory in CrewAI
Module 7 · Advanced Crews | Read first: md/07-advanced-crews/7_2_memory.md

What you'll learn:
  Part 1: Memory on its own: remember facts, then recall them by MEANING
          (not exact words). The LLM auto-tags each memory with categories.
  Part 2: Memory in a crew: run 1 learns about the user, run 2 (a brand-new
          crew sharing the same memory) uses it without being told again.

Memory needs an EMBEDDER (turns text into numbers so similar meanings match).
We use NVIDIA's embedding model with the same API key, through a tiny custom
embedder class (NVIDIA's model needs an extra "input_type" setting).

Run (from the repo root):
  .venv\\Scripts\\python code\\07-advanced-crews\\7_2_memory.py
"""

import os
import re
import sys
from pathlib import Path

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
sys.stdout.reconfigure(encoding="utf-8")

from crewai import LLM, Agent, Crew, Task
from crewai.memory.storage.lancedb_storage import LanceDBStorage
from crewai.memory.unified_memory import Memory
from crewai.rag.embeddings.providers.custom.embedding_callable import CustomEmbeddingFunction
from openai import OpenAI

# --- LLM setup: read the NVIDIA key from settings.config (repo root) ---
SETTINGS = Path(__file__).resolve().parents[2] / "settings.config"
cfg = dict(re.findall(r"^[ \t]*(\w+)[ \t]*=[ \t]*['\"]?(.*?)['\"]?[ \t]*$", SETTINGS.read_text(encoding="utf-8"), re.M))
API_KEY = cfg.get("NVIDIA_API_KEY") or cfg["NVDIA_API_KEY"]
llm = LLM(
    model=cfg.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
    custom_openai=True,
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=API_KEY,
)

# --- The embedder: text in -> list of numbers out ---
nvidia = OpenAI(base_url="https://integrate.api.nvidia.com/v1", api_key=API_KEY)


class NvidiaEmbedder(CustomEmbeddingFunction):
    def __call__(self, input):
        response = nvidia.embeddings.create(
            model="nvidia/nemotron-3-embed-1b",
            input=list(input),
            extra_body={"input_type": "query"},  # NVIDIA-specific; without it, matches are poor
        )
        return [item.embedding for item in response.data]


# --- The memory: an LLM (to analyse what's saved), the embedder, and storage ---
memory = Memory(
    llm=llm,
    embedder={"provider": "custom", "config": {"embedding_callable": NvidiaEmbedder}},
    # A recall score mixes meaning + recency + importance. For facts like these,
    # meaning should win, so we weight it at 90%. (Defaults: 0.5 / 0.3 / 0.2.)
    semantic_weight=0.9,
    recency_weight=0.05,
    importance_weight=0.05,
    storage=LanceDBStorage(path=Path(__file__).parent / "output" / "memory_db"),  # a local folder
)
memory.reset()  # start clean so the demo is repeatable

# ---------------------------------------------------------------
# Part 1: Memory as a smart notebook
# ---------------------------------------------------------------
print("===== PART 1: remember and recall =====\n")
for fact in [
    "Our team stand-up is every weekday at 9:30 in room Orion.",
    "The production database is PostgreSQL 16, hosted in Frankfurt.",
    "Priya is the on-call engineer this week.",
]:
    memory.remember(fact)
memory.drain_writes()  # wait until all saves are finished

# Recall returns RANKED candidates (closest meaning first), not one "right answer".
# Crews pass the top few to the agent, and the LLM picks what's relevant.
for question in ["What time is the daily team meeting?", "Who should I call if the site goes down?", "Which database do we use?"]:
    print(f"Q: {question}")
    for rank, match in enumerate(memory.recall(question, limit=2), 1):
        print(f"   {rank}. {match.record.content}  (score {match.score:.2f})")
    print()
print(f"Auto-categories the LLM assigned: {memory.info().categories}\n")

# ---------------------------------------------------------------
# Part 2: Memory shared by crews
# ---------------------------------------------------------------
print("===== PART 2: run 1 learns, run 2 remembers =====\n")
memory.reset()


def assistant_crew(request: str) -> str:
    helper = Agent(role="Personal Assistant", goal="Help the user, using what you know about them", backstory="Attentive and personal.", llm=llm)
    task = Task(description=request, expected_output="A short, helpful reply.", agent=helper)
    return Crew(agents=[helper], tasks=[task], memory=memory).kickoff().raw.strip()


print("RUN 1 ->", assistant_crew("The user says: 'Hi, I'm Venkata. I'm vegetarian and allergic to peanuts.' Greet them and confirm."))
memory.drain_writes()
# Run 2 is NOT told the user's diet. It must come from memory. We only ask it to respect what it remembers.
print("\nRUN 2 ->", assistant_crew("Suggest one dinner recipe for the user tonight that respects everything you remember about them. Do not ask questions."))

memory.drain_writes()
records = memory.list_records()
print(f"\n===== WHAT THE CREWS SAVED: {len(records)} small facts. The ones about the user: =====\n")
for record in records:
    if "Venkata" in record.content:
        print(f"  • {record.content[:110]}")

# ---------------------------------------------------------------
# Takeaways
#   - Memory = remember() + recall() by meaning, backed by an embedder + a vector DB.
#   - Recall is only as good as the embedder: check that the right fact wins.
#   - Crew(memory=...) saves what it learns after tasks and recalls it before tasks.
#   - Share one Memory object between crews/runs for long-term "knowledge of the user".
#   - memory.reset() wipes it: do that between tests.
