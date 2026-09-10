"""Chemoinformatics agent node."""

from __future__ import annotations

from bioagent.state import DiscoveryState
from bioagent.tools.chembl_tool import find_target, get_ranked_compounds

SYSTEM_PROMPT = """You are the Chemoinformatics Agent. Work only with ChEMBL data returned by tools. Prioritize unique small molecules with quantified IC50 or Ki values in nM, ranking lower values first. Never infer activity, selectivity, or clinical efficacy beyond returned data."""


def chemoinformatics_node(state: DiscoveryState) -> DiscoveryState:
    """Resolve the target in ChEMBL and retrieve five potency-ranked compounds."""
    errors = list(state.get("errors", []))
    query_terms = [state.get("target_symbol"), state.get("target_protein"), state.get("target_uniprot_id")]
    target = None
    for term in filter(None, query_terms):
        try:
            target = find_target(term)
            if target:
                break
        except Exception as exc:
            errors.append(f"ChEMBL target lookup failed for '{term}': {exc}")
    if not target:
        return {"candidate_molecules": [], "errors": errors + ["Target could not be resolved in ChEMBL."], "target_chembl_id": None}
    target_id = target.get("target_chembl_id")
    try:
        candidates = get_ranked_compounds(target_id, limit=5)
        if not candidates:
            errors.append("No IC50/Ki compounds with usable SMILES were returned by ChEMBL.")
        return {"target_chembl_id": target_id, "candidate_molecules": candidates, "errors": errors}
    except Exception as exc:
        return {"target_chembl_id": target_id, "candidate_molecules": [], "errors": errors + [f"ChEMBL activity retrieval failed: {exc}"]}
