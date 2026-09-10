"""Europe PMC client used as the medical-literature retrieval tool."""

from __future__ import annotations

from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

EUROPE_PMC_SEARCH_URL = "https://www.ebi.ac.uk/europepmc/webservices/rest/search"


def _session() -> requests.Session:
    """Create an HTTP session with retry and backoff."""
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.6, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=("GET",))
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def search_literature(disease_term: str, limit: int = 8) -> list[dict[str, Any]]:
    """Return recent Europe PMC records with non-empty abstracts.

    Args:
        disease_term: Disease or synonym to search.
        limit: Maximum records requested from the service.

    Returns:
        Normalized literature records. An empty list means no usable result.
    """
    query = f'("{disease_term}") AND (TITLE_ABS:protein OR TITLE_ABS:target OR TITLE_ABS:therapeutic)'
    params = {"query": query, "format": "json", "resultType": "core", "pageSize": limit, "sort": "FIRST_PDATE_D"}
    response = _session().get(EUROPE_PMC_SEARCH_URL, params=params, timeout=25)
    response.raise_for_status()
    records = response.json().get("resultList", {}).get("result", [])
    return [
        {
            "pmid": item.get("pmid"),
            "pmcid": item.get("pmcid"),
            "doi": item.get("doi"),
            "title": item.get("title", ""),
            "abstract": item.get("abstractText", ""),
            "journal": item.get("journalTitle", ""),
            "published": item.get("firstPublicationDate", ""),
        }
        for item in records
        if item.get("abstractText")
    ]
