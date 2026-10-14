"""
6.1 Structured Outputs with Pydantic
Module 6 · Reliable Outputs | Read first: md/06-reliable-outputs/6_1_structured_outputs.md

What you'll learn:
  Free text is hard for code to use. With output_pydantic=YourModel,
  CrewAI returns a typed Python object instead, so you can do:
      job.salary_max, job.remote, job.skills ...
  Demo: turn a messy job advert into a clean JobPosting object,
  then use its fields in plain Python.

Run (from the repo root):
  .venv\\Scripts\\python code\\06-reliable-outputs\\6_1_structured_outputs.py
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


# 1) Describe the SHAPE you want. Field descriptions guide the LLM.
class JobPosting(BaseModel):
    title: str
    company: str
    location: str
    remote: bool = Field(description="True if remote or hybrid work is allowed")
    salary_min: int | None = Field(description="Yearly minimum in GBP, or null if not stated")
    salary_max: int | None = Field(description="Yearly maximum in GBP, or null if not stated")
    skills: list[str] = Field(description="Required technical skills, lowercase")
    years_experience: int | None = Field(description="Minimum years of experience, or null")


MESSY_AD = """
🚀 WE'RE HIRING!!! Acme Robotics (Manchester office, but 3 days WFH ok)
is looking for a Backend Engineer to join the Rocket team. You'll write Python
& some Go, work with PostgreSQL, Docker and AWS. Need 3+ yrs exp.
Pay: £55k-£70k + shares. Apply by Friday!!
"""

parser = Agent(
    role="Job Ad Parser",
    goal="Extract accurate, structured data from job adverts",
    backstory="You read job ads all day and never invent details that aren't there.",
    llm=llm,
)

parse = Task(
    description="Extract the job details from this advert:\n{ad}",
    expected_output="The job details as structured data.",
    agent=parser,
    output_pydantic=JobPosting,  # 2) <- ask for a JobPosting object back
)

result = Crew(agents=[parser], tasks=[parse]).kickoff(inputs={"ad": MESSY_AD})

# 3) result.pydantic is a real JobPosting: typed fields, no text parsing.
job: JobPosting = result.pydantic

print("\n===== THE OBJECT =====\n")
print(job.model_dump_json(indent=2))

print("\n===== USING IT IN PLAIN PYTHON =====\n")
my_skills = {"python", "postgresql", "react"}
matched = my_skills & set(job.skills)
print(f"Role         : {job.title} at {job.company} ({job.location})")
print(f"Remote OK?   : {'yes' if job.remote else 'no'}")
if job.salary_min and job.salary_max:
    print(f"Mid salary   : £{(job.salary_min + job.salary_max) / 2:,.0f}")
print(f"Skill match  : {len(matched)}/{len(job.skills)} -> {sorted(matched)}")
print(f"Apply?       : {'✅ yes' if len(matched) >= 2 and job.remote else '🤔 maybe'}")

# ---------------------------------------------------------------
# Takeaways
#   - output_pydantic=Model -> result.pydantic is a validated object.
#   - output_json=Model     -> result.json_dict is a plain dict instead.
#   - Field(description=...) is how you explain each field to the LLM.
#   - Use None for "may be missing" so the LLM isn't forced to invent values.
