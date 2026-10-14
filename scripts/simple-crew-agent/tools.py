"""
The agent's "hands": two tools for reading about a country.

- read_wikipedia     -> the article text (history, geography, culture ...)
- get_country_facts  -> exact numbers from Wikidata (capital, population, area ...)

Both use free public APIs - no key needed.
"""

import requests
from crewai.tools import tool

WIKI_API = "https://en.wikipedia.org/w/api.php"
WIKIDATA_SPARQL = "https://query.wikidata.org/sparql"
HEADERS = {"User-Agent": "crew-ai-masterclass/1.0 (learning project)"}
MAX_CHARS = 8000  # keep the article small enough for the LLM's context window

# Wikidata property IDs: P36 capital, P1082 population, P2046 area,
# P37 official language, P38 currency, P30 continent, P122 government.
FACTS_QUERY = """
SELECT
  (GROUP_CONCAT(DISTINCT ?capitalLabel; separator=", ") AS ?capital)
  (MAX(?pop) AS ?population)
  (MAX(?ar) AS ?area_km2)
  (GROUP_CONCAT(DISTINCT ?languageLabel; separator=", ") AS ?official_languages)
  (GROUP_CONCAT(DISTINCT ?currencyLabel; separator=", ") AS ?currency)
  (GROUP_CONCAT(DISTINCT ?continentLabel; separator=", ") AS ?continent)
  (GROUP_CONCAT(DISTINCT ?govLabel; separator=", ") AS ?government)
WHERE {
  <ARTICLE_URL> schema:about ?item .
  OPTIONAL { ?item wdt:P36 ?c . ?c rdfs:label ?capitalLabel FILTER(LANG(?capitalLabel)="en") }
  OPTIONAL { ?item wdt:P1082 ?pop }
  OPTIONAL { ?item wdt:P2046 ?ar }
  OPTIONAL { ?item wdt:P37 ?l . ?l rdfs:label ?languageLabel FILTER(LANG(?languageLabel)="en") }
  OPTIONAL { ?item wdt:P38 ?cu . ?cu rdfs:label ?currencyLabel FILTER(LANG(?currencyLabel)="en") }
  OPTIONAL { ?item wdt:P30 ?co . ?co rdfs:label ?continentLabel FILTER(LANG(?continentLabel)="en") }
  OPTIONAL { ?item wdt:P122 ?g . ?g rdfs:label ?govLabel FILTER(LANG(?govLabel)="en") }
}
"""


def _wiki_get(params: dict) -> dict:
    resp = requests.get(WIKI_API, params={**params, "format": "json"}, headers=HEADERS, timeout=30)
    resp.raise_for_status()
    return resp.json()


def _resolve_title(country: str) -> str | None:
    """Turn a user's country name into the exact Wikipedia article title."""
    # 1. Exact title, following redirects ("USA" -> "United States").
    page = next(iter(_wiki_get({"action": "query", "redirects": 1, "titles": country})["query"]["pages"].values()))
    if "missing" not in page and "invalid" not in page:
        return page["title"]
    # 2. Fall back to Wikipedia search.
    hits = _wiki_get({"action": "query", "list": "search", "srsearch": f"{country} country", "srlimit": 1})["query"]["search"]
    return hits[0]["title"] if hits else None


def _article_url(title: str) -> str:
    return f"https://en.wikipedia.org/wiki/{title.replace(' ', '_')}"


@tool("Read Wikipedia article")
def read_wikipedia(country: str) -> str:
    """Read the English Wikipedia article about a country and return its plain text
    (history, geography, economy, culture). Input: the country name, e.g. 'Japan'."""
    try:
        title = _resolve_title(country)
        if not title:
            return f"No Wikipedia article found for '{country}'."
        pages = _wiki_get({"action": "query", "prop": "extracts", "explaintext": 1, "titles": title})["query"]["pages"]
        text = next(iter(pages.values())).get("extract", "")
        if len(text) > MAX_CHARS:
            text = text[:MAX_CHARS] + "\n\n[...article truncated...]"
        return f"SOURCE: {_article_url(title)}\nTITLE: {title}\n\n{text}"
    except requests.RequestException as e:
        return f"Error reading Wikipedia: {e}"


@tool("Get country quick facts")
def get_country_facts(country: str) -> str:
    """Get exact quick facts about a country from Wikidata: capital, population,
    area in km², official languages, currency, continent and government.
    Input: the country name, e.g. 'Japan'."""
    try:
        title = _resolve_title(country)
        if not title:
            return f"No data found for '{country}'."
        query = FACTS_QUERY.replace("ARTICLE_URL", _article_url(title))
        resp = requests.get(WIKIDATA_SPARQL, params={"query": query, "format": "json"}, headers=HEADERS, timeout=60)
        resp.raise_for_status()
        rows = resp.json()["results"]["bindings"]
        facts = {key: value["value"] for key, value in rows[0].items() if value["value"]} if rows else {}
        if not facts:
            return f"No Wikidata facts found for '{title}'."
        lines = [f"{key}: {value}" for key, value in facts.items()]
        return "SOURCE: https://www.wikidata.org (via " + _article_url(title) + ")\n" + "\n".join(lines)
    except requests.RequestException as e:
        return f"Error reading Wikidata: {e}"
