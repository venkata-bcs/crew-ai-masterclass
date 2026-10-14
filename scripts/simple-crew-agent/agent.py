"""
The worker: one agent that researches a country.

role + goal + backstory become the agent's hidden instructions to the LLM.
{country} is filled in at kickoff time from the inputs.
"""

from crewai import LLM, Agent

from tools import get_country_facts, read_wikipedia


def create_country_researcher(llm: LLM) -> Agent:
    return Agent(
        role="Country Researcher",
        goal="Read reliable information about {country} and turn it into a clear, accurate fact sheet.",
        backstory=(
            "You are a geography teacher who writes study notes for beginners. "
            "You only state facts you have read in your sources, and you never make up numbers."
        ),
        tools=[get_country_facts, read_wikipedia],
        llm=llm,
        allow_delegation=False,  # works alone, no teammates to ask
        max_iter=5,  # cap the think -> act -> observe loop
        verbose=True,  # print the Thought / Action / Observation steps
    )
