"""
The to-do item: research a country and write a Markdown fact sheet.

expected_output is the "definition of done". The more exact it is,
the more consistent the result.
"""

from pathlib import Path

from crewai import Agent, Task

REPORT_TEMPLATE = """\
# <Country name>

> One-sentence summary of the country.

## Quick Facts
| Fact | Value |
|---|---|
| Capital | ... |
| Continent / Region | ... |
| Population | ... |
| Area | ... |
| Official language(s) | ... |
| Currency | ... |
| Government | ... |

## Overview
2-3 short paragraphs.

## History
5-8 bullet points, oldest to newest.

## Geography & Climate
3-5 bullet points.

## Economy
3-5 bullet points.

## Culture
3-5 bullet points (food, festivals, arts, sport).

## Fun Facts
3 surprising facts.

## Sources
- <Wikipedia URL from the tool output>
- Wikidata (quick facts)
"""


def create_country_report_task(agent: Agent, output_file: Path) -> Task:
    return Task(
        description=(
            "Research {country} in two steps:\n"
            "1. Use the 'Get country quick facts' tool for the Quick Facts table "
            "(format big numbers with commas, area in km²).\n"
            "2. Use the 'Read Wikipedia article' tool for everything else.\n"
            "Then write a beginner-friendly fact sheet using ONLY facts from what you read. "
            "If a fact is not in the article, write 'Not found' instead of guessing."
        ),
        expected_output=(
            "A Markdown document that follows this template exactly "
            "(raw Markdown only, do not wrap it in ``` code fences):\n\n" + REPORT_TEMPLATE
        ),
        agent=agent,
        output_file=str(output_file),  # CrewAI writes the final answer here
    )
