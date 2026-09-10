"""ChEMBL REST client for targets, activities, and molecular structures."""

from __future__ import annotations

from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

CHEMBL_BASE_URL = "https://www.ebi.ac.uk/chembl/api/data"


def _session() -> requests.Session:
    """Create a retry-enabled client for the ChEMBL REST API."""
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.6, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=("GET",))
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def _documents(payload: dict[str, Any]) -> list[dict[str, Any]]:
    """Handle the ChEMBL response collection envelope."""
    return payload.get("_embedded", {}).get("documents", [])


def find_target(query: str) -> dict[str, Any] | None:
    """Resolve a protein symbol/name against ChEMBL target records."""
    response = _session().get(
        f"{CHEMBL_BASE_URL}/target/search.json",
        params={"q": query, "limit": 20},
        timeout=25,
    )
    response.raise_for_status()
    candidates = _documents(response.json())
    human_single_protein = [x for x in candidates if x.get("organism") == "Homo sapiens" and x.get("target_type") == "SINGLE PROTEIN"]
    return (human_single_protein or candidates or [None])[0]


def get_ranked_compounds(target_chembl_id: str, limit: int = 5) -> list[dict[str, Any]]:
    """Retrieve IC50/Ki activities and rank unique molecules by potency in nM."""
    params = {
        "target_chembl_id": target_chembl_id,
        "standard_type__in": "IC50,Ki",
        "standard_relation__in": "=,<,<=",
        "standard_units": "nM",
        "standard_value__isnull": "false",
        "limit": 100,
    }
    response = _session().get(f"{CHEMBL_BASE_URL}/activity.json", params=params, timeout=25)
    response.raise_for_status()
    activities = _documents(response.json())
    best: dict[str, dict[str, Any]] = {}
    for activity in activities:
        molecule_id = activity.get("molecule_chembl_id")
        try:
            value = float(activity.get("standard_value"))
        except (TypeError, ValueError):
            continue
        if not molecule_id or value <= 0:
            continue
        row = {
            "chembl_id": molecule_id,
            "activity_type": activity.get("standard_type"),
            "activity_value_nm": value,
            "assay_chembl_id": activity.get("assay_chembl_id"),
            "pchembl_value": activity.get("pchembl_value"),
        }
        if molecule_id not in best or value < best[molecule_id]["activity_value_nm"]:
            best[molecule_id] = row
    ranked = sorted(best.values(), key=lambda item: item["activity_value_nm"])
    output: list[dict[str, Any]] = []
    for activity in ranked:
        molecule_response = _session().get(f"{CHEMBL_BASE_URL}/molecule/{activity['chembl_id']}.json", timeout=25)
        if molecule_response.status_code != 200:
            continue
        molecule = molecule_response.json()
        structures = molecule.get("molecule_structures") or {}
        smiles = structures.get("canonical_smiles")
        if not smiles:
            continue
        output.append({**activity, "compound_name": molecule.get("pref_name") or activity["chembl_id"], "smiles": smiles})
        if len(output) >= limit:
            break
    return output
