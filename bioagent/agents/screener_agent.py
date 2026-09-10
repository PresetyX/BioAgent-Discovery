"""Safety screening and Markdown reporting agent node."""

from __future__ import annotations

from bioagent.state import DiscoveryState
from bioagent.tools.pubchem_tool import screen_smiles

SYSTEM_PROMPT = """You are the Screener & Safety Agent. You must distinguish data retrieval from safety evidence. Lipinski-style property flags are only coarse drug-likeness screens; they do not prove toxicity, pharmacokinetics, clinical safety, or efficacy. Use cautious scientific language and recommend experimental validation."""


def _report(state: DiscoveryState, screened: list[dict]) -> str:
    """Produce a deterministic, auditable Markdown report from collected data."""
    rows = []
    for item in screened:
        compound = item["compound"]
        safety = item["safety"]
        if safety.get("screening_status") == "REJECT":
            continue
        rows.append(
            f"### {compound['compound_name']} ({compound['chembl_id']})\n"
            f"- **SMILES:** `{compound['smiles']}`\n"
            f"- **Best reported activity:** {compound['activity_type']} {compound['activity_value_nm']:.3g} nM\n"
            f"- **ChEMBL assay:** {compound.get('assay_chembl_id', 'N/A')}\n"
            f"- **PubChem CID:** {safety.get('pubchem_cid', 'Not resolved')}\n"
            f"- **Properties:** MW {safety.get('molecular_weight', 'N/A')}, XLogP {safety.get('xlogp', 'N/A')}, HBD {safety.get('hbd', 'N/A')}, HBA {safety.get('hba', 'N/A')}, TPSA {safety.get('tpsa', 'N/A')}\n"
            f"- **Coarse screen:** {safety.get('screening_status', 'MANUAL REVIEW')} ({safety.get('lipinski_violations', 'N/A')} Lipinski-style flags)\n"
            f"- **Rationale:** Potency-ranked candidate; requires selectivity, ADME, toxicity, and experimental validation.\n"
        )
    candidates_text = "\n".join(rows) or "No candidates passed the coarse property screen; manual review is required."
    literature = "\n".join(f"- PMID {x.get('pmid', 'N/A')}: {x['title']}" for x in state.get("literature", [])[:5]) or "- No abstracts retained"
    return f"""# BioAgent-Discovery: Drug Candidate Report

## Executive Summary
- **Disease:** {state.get('disease', 'N/A')}
- **Proposed protein target:** {state.get('target_protein', 'N/A')} ({state.get('target_symbol', 'N/A')})
- **Target confidence:** {state.get('target_confidence', 'N/A')}
- **Candidates screened:** {len(screened)}
- **Candidates retained:** {sum(1 for x in screened if x['safety'].get('screening_status') != 'REJECT')}

## Target Rationale
{state.get('target_justification', 'No target rationale available.')}

## Literature Retrieved
{literature}

## Candidate Molecules
{candidates_text}

## Methodology
- Literature retrieval: Europe PMC REST API.
- Bioactivity retrieval: ChEMBL REST API, restricted to quantified IC50/Ki records in nM where available.
- Property triage: PubChem PUG REST API with Lipinski-style thresholds (MW <= 500, XLogP <= 5, HBD <= 5, HBA <= 10).

## Limitations
This report is a research prioritization artifact, not evidence of therapeutic efficacy or safety. Public database records can be incomplete, context-dependent, or inconsistent across assays. The workflow does not establish target engagement, selectivity, exposure, metabolism, toxicity, dosage, or clinical suitability.

## Recommended Next Steps
1. Verify target-disease causality and mechanism using domain-expert review.
2. Inspect original ChEMBL assay protocols and replicate potency measurements.
3. Run medicinal-chemistry, selectivity, ADME, and in-vitro toxicity evaluation before any downstream decision.
"""


def screening_node(state: DiscoveryState) -> DiscoveryState:
    """Enrich candidates with PubChem properties and write a Markdown report."""
    errors = list(state.get("errors", []))
    screened = []
    for compound in state.get("candidate_molecules", []):
        try:
            safety = screen_smiles(compound["smiles"])
        except Exception as exc:
            errors.append(f"PubChem screen failed for {compound.get('chembl_id')}: {exc}")
            safety = {"screening_status": "MANUAL REVIEW", "flags": ["PubChem resolution failed"]}
        screened.append({"compound": compound, "safety": safety})
    return {"screened_molecules": screened, "final_report": _report(state, screened), "errors": errors}
