"""Generate `sample_report.md` by running the real LangGraph pipeline with canned data.

The APIs (Europe PMC, ChEMBL, PubChem) and the LLM are replaced by deterministic fakes, so
the report shows the exact format produced by the system without network access or API keys.
All identifiers and values are SYNTHETIC and must not be read as scientific results.

Usage:
    python scripts/generate_sample_report.py
"""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from bioagent.graph import run_pipeline  # noqa: E402
from bioagent.state import TargetExtraction  # noqa: E402

DISCLAIMER = """> **Demonstration output.** This file was produced by running the real BioAgent-Discovery
> LangGraph pipeline (`scripts/generate_sample_report.py`) with simulated API responses.
> Every PMID, ChEMBL ID, potency and property below is **synthetic**: it shows the report
> format, not a scientific finding. Run `python main.py --disease "..."` with an API key to
> produce a report from live data.

"""

LITERATURE = [
    {"pmid": "DEMO-0001", "title": "Synthetic record: beta-secretase activity and amyloid processing", "abstract": "Demo."},
    {"pmid": "DEMO-0002", "title": "Synthetic record: protease inhibition strategies in neurodegeneration", "abstract": "Demo."},
    {"pmid": "DEMO-0003", "title": "Synthetic record: biomarkers for early-stage disease monitoring", "abstract": "Demo."},
]

TARGET = TargetExtraction(
    target_protein="Beta-secretase 1",
    target_symbol="BACE1",
    uniprot_id="P56817",
    justification=(
        "In the (synthetic) retrieved abstracts, BACE1 is repeatedly described as the enzyme that "
        "initiates amyloid precursor protein processing, making it the most frequently cited "
        "actionable protein target. Evidence is literature-derived and requires expert review."
    ),
    confidence="MEDIUM",
)

COMPOUNDS = [
    {"chembl_id": "CHEMBL-DEMO-001", "compound_name": "DEMO COMPOUND A", "smiles": "CC(C)Cc1ccc(cc1)C(C)C(=O)N", "activity_type": "IC50", "activity_value_nm": 4.2, "assay_chembl_id": "ASSAY-DEMO-11"},
    {"chembl_id": "CHEMBL-DEMO-002", "compound_name": "DEMO COMPOUND B", "smiles": "COc1ccc2[nH]cc(CCN)c2c1", "activity_type": "Ki", "activity_value_nm": 9.8, "assay_chembl_id": "ASSAY-DEMO-12"},
    {"chembl_id": "CHEMBL-DEMO-003", "compound_name": "DEMO COMPOUND C", "smiles": "CCCCCCCCCCCCCCCC(=O)NC(Cc1ccccc1)C(=O)O", "activity_type": "IC50", "activity_value_nm": 15.0, "assay_chembl_id": "ASSAY-DEMO-13"},
    {"chembl_id": "CHEMBL-DEMO-004", "compound_name": "DEMO COMPOUND D", "smiles": "CN1CCN(CC1)c1ccc(NC(=O)c2ccccc2)cc1", "activity_type": "IC50", "activity_value_nm": 27.5, "assay_chembl_id": "ASSAY-DEMO-14"},
    {"chembl_id": "CHEMBL-DEMO-005", "compound_name": "DEMO COMPOUND E", "smiles": "DEMO-REJECTED-SMILES", "activity_type": "Ki", "activity_value_nm": 31.0, "assay_chembl_id": "ASSAY-DEMO-15"},
]

SCREENS = {
    "CC(C)Cc1ccc(cc1)C(C)C(=O)N": {"pubchem_cid": "DEMO-101", "molecular_weight": 205.3, "xlogp": 3.1, "hbd": 1, "hba": 1, "tpsa": 43.1, "lipinski_violations": 0, "screening_status": "PASS"},
    "COc1ccc2[nH]cc(CCN)c2c1": {"pubchem_cid": "DEMO-102", "molecular_weight": 190.2, "xlogp": 1.2, "hbd": 2, "hba": 2, "tpsa": 51.0, "lipinski_violations": 0, "screening_status": "PASS"},
    "CCCCCCCCCCCCCCCC(=O)NC(Cc1ccccc1)C(=O)O": {"pubchem_cid": "DEMO-103", "molecular_weight": 612.4, "xlogp": 7.8, "hbd": 2, "hba": 3, "tpsa": 66.4, "lipinski_violations": 2, "screening_status": "CAUTION"},
    # Four Lipinski-style flags -> REJECT, so it is screened but left out of the report.
    "DEMO-REJECTED-SMILES": {"pubchem_cid": "DEMO-105", "molecular_weight": 845.0, "xlogp": 6.9, "hbd": 7, "hba": 14, "tpsa": 210.0, "lipinski_violations": 4, "screening_status": "REJECT"},
    "CN1CCN(CC1)c1ccc(NC(=O)c2ccccc2)cc1": {"pubchem_cid": "DEMO-104", "molecular_weight": 295.4, "xlogp": 2.4, "hbd": 1, "hba": 3, "tpsa": 35.6, "lipinski_violations": 0, "screening_status": "PASS"},
}


class _Extractor:
    def invoke(self, messages):
        return TARGET


class _LLM:
    def with_structured_output(self, schema):
        return _Extractor()


def main() -> None:
    with (
        patch("bioagent.agents.medical_agent.search_literature", lambda term: LITERATURE),
        patch("bioagent.agents.medical_agent._llm", lambda: _LLM()),
        patch("bioagent.agents.chemoinformatics_agent.find_target", lambda term: {"target_chembl_id": "CHEMBL-DEMO-T1"}),
        patch("bioagent.agents.chemoinformatics_agent.get_ranked_compounds", lambda tid, limit: COMPOUNDS[:limit]),
        patch("bioagent.agents.screener_agent.screen_smiles", lambda smiles: SCREENS[smiles]),
    ):
        state = run_pipeline("Alzheimer's disease")

    output = ROOT / "sample_report.md"
    output.write_text(DISCLAIMER + state["final_report"], encoding="utf-8")
    print(f"Sample report written to {output}")


if __name__ == "__main__":
    main()
