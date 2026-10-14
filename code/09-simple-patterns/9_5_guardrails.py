"""
9.5 Pattern: Guardrails
Module 9 · Simple Patterns | Read first: md/09-simple-patterns/9_5_guardrails.md

PROBLEM:  An AI writes product descriptions for your shop. Two rules:
            1) at most 30 words (it must fit on the product card)
            2) it must show the price, "$49"
          AIs sometimes break rules like these.
SOLUTION: A guardrail: a small Python function that CHECKS the answer.
          If a rule is broken, the agent is told what's wrong and tries again.

Run (from the repo root):
  .venv\\Scripts\\python code\\09-simple-patterns\\9_5_guardrails.py
"""

import os
import re
import sys
from pathlib import Path

os.environ.setdefault("CREWAI_DISABLE_TELEMETRY", "true")
os.environ.setdefault("OTEL_SDK_DISABLED", "true")
sys.stdout.reconfigure(encoding="utf-8")

from crewai import LLM, Agent, Crew, Task

# --- LLM setup: read the NVIDIA key from settings.config (repo root) ---
SETTINGS = Path(__file__).resolve().parents[2] / "settings.config"
cfg = dict(re.findall(r"^[ \t]*(\w+)[ \t]*=[ \t]*['\"]?(.*?)['\"]?[ \t]*$", SETTINGS.read_text(encoding="utf-8"), re.M))
llm = LLM(
    model=cfg.get("NVIDIA_MODEL", "nvidia/nemotron-3-super-120b-a12b"),
    custom_openai=True,
    base_url="https://integrate.api.nvidia.com/v1",
    api_key=cfg.get("NVIDIA_API_KEY") or cfg["NVDIA_API_KEY"],
)

attempt = 0


# The guardrail: check the rules, return (passed?, value or feedback)
def check_description(output):
    global attempt
    attempt += 1
    text = output.raw.strip()
    words = len(text.split())

    if words > 30:
        print(f"   ❌ attempt {attempt}: {words} words, too long")
        return (False, f"Too long: {words} words. Use 30 words or fewer.")
    if "$49" not in text:
        print(f"   ❌ attempt {attempt}: price missing")
        return (False, "You forgot the price. Include '$49' exactly.")

    print(f"   ✅ attempt {attempt}: {words} words, price included")
    return (True, text)


copywriter = Agent(
    role="Product Copywriter",
    goal="Write exciting product descriptions",
    backstory="You love describing every single feature in rich detail.",  # tempts it to write too much!
    llm=llm,
)

describe = Task(
    description="Write a product description for: a smart water bottle that glows when you forget to drink. Price: $49.",
    expected_output="A product description.",
    agent=copywriter,
    guardrail=check_description,  # <- check every answer
    guardrail_max_retries=3,  # <- give up after 3 retries
)

print("🛡️ Checking each attempt:")
result = Crew(agents=[copywriter], tasks=[describe]).kickoff()

print("\n🏷️ FINAL DESCRIPTION:\n")
print(result.raw.strip())

# ---------------------------------------------------------------
# Takeaways
#   - A guardrail is just a function: return (True, value) or (False, "what to fix").
#   - The feedback text goes back to the agent, so say exactly what's wrong.
#   - Use guardrails for rules you can check with code: length, required words, format.
