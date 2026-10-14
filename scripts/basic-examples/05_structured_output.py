"""
05 - Structured output: get a Python object back instead of free text.

`output_pydantic=Model` makes CrewAI turn the answer into a typed object,
so your code can use result.pydantic.title, .year, ... directly.
Run:  .venv\\Scripts\\python scripts\\basic-examples\\05_structured_output.py "space adventure"
"""

import os
import re
import sys
from pathlib import Path

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
sys.stdout.reconfigure(encoding="utf-8")

from crewai import LLM, Agent, Crew, Task
from pydantic import BaseModel, Field

# --- LLM setup: read the NVIDIA key from settings.config (repo root) ---
SETTINGS = Path(__file__).resolve().parents[2] / "settings.config"
cfg = dict(re.findall(r"^[ \t]*(\w+)[ \t]*=[ \t]*['\"]?(.*?)['\"]?[ \t]*$", SETTINGS.read_text(encoding="utf-8"), re.M))
llm = LLM(
    model=cfg.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
    custom_openai=True,
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=cfg.get("NVIDIA_API_KEY") or cfg["NVDIA_API_KEY"],
)


# The shape we want back
class Movie(BaseModel):
    title: str
    year: int
    director: str
    reason: str = Field(description="One sentence on why it matches the request")


class MovieList(BaseModel):
    movies: list[Movie]


critic = Agent(
    role="Film Critic",
    goal="Recommend well-known movies that match a mood or genre",
    backstory="You have watched thousands of films and only recommend real ones.",
    llm=llm,
)

task = Task(
    description="Recommend 3 real movies for someone who wants: {wish}.",
    expected_output="3 movies with title, year, director and a one-sentence reason.",
    agent=critic,
    output_pydantic=MovieList,  # <- typed result
)

wish = sys.argv[1] if len(sys.argv) > 1 else "a feel-good space adventure"
result = Crew(agents=[critic], tasks=[task]).kickoff(inputs={"wish": wish})

movies: MovieList = result.pydantic
for i, m in enumerate(movies.movies, 1):
    print(f"{i}. {m.title} ({m.year}), dir. {m.director}\n   {m.reason}")

print("\nAs JSON:\n", movies.model_dump_json(indent=2))
