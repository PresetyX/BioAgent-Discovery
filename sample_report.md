> **Demonstration output.** This file was produced by running the real BioAgent-Discovery
> LangGraph pipeline (`scripts/generate_sample_report.py`) with simulated API responses.
> Every PMID, ChEMBL ID, potency and property below is **synthetic**: it shows the report
> format, not a scientific finding. Run `python main.py --disease "..."` with an API key to
> produce a report from live data.

# BioAgent-Discovery: Drug Candidate Report

## Executive Summary
- **Disease:** Alzheimer's disease
- **Proposed protein target:** Beta-secretase 1 (BACE1)
- **Target confidence:** MEDIUM
- **Candidates screened:** 5
- **Candidates retained:** 4

## Target Rationale
In the (synthetic) retrieved abstracts, BACE1 is repeatedly described as the enzyme that initiates amyloid precursor protein processing, making it the most frequently cited actionable protein target. Evidence is literature-derived and requires expert review.

## Literature Retrieved
- PMID DEMO-0001: Synthetic record: beta-secretase activity and amyloid processing
- PMID DEMO-0002: Synthetic record: protease inhibition strategies in neurodegeneration
- PMID DEMO-0003: Synthetic record: biomarkers for early-stage disease monitoring

## Candidate Molecules
### DEMO COMPOUND A (CHEMBL-DEMO-001)
- **SMILES:** `CC(C)Cc1ccc(cc1)C(C)C(=O)N`
- **Best reported activity:** IC50 4.2 nM
- **ChEMBL assay:** ASSAY-DEMO-11
- **PubChem CID:** DEMO-101
- **Properties:** MW 205.3, XLogP 3.1, HBD 1, HBA 1, TPSA 43.1
- **Coarse screen:** PASS (0 Lipinski-style flags)
- **Rationale:** Potency-ranked candidate; requires selectivity, ADME, toxicity, and experimental validation.

### DEMO COMPOUND B (CHEMBL-DEMO-002)
- **SMILES:** `COc1ccc2[nH]cc(CCN)c2c1`
- **Best reported activity:** Ki 9.8 nM
- **ChEMBL assay:** ASSAY-DEMO-12
- **PubChem CID:** DEMO-102
- **Properties:** MW 190.2, XLogP 1.2, HBD 2, HBA 2, TPSA 51.0
- **Coarse screen:** PASS (0 Lipinski-style flags)
- **Rationale:** Potency-ranked candidate; requires selectivity, ADME, toxicity, and experimental validation.

### DEMO COMPOUND C (CHEMBL-DEMO-003)
- **SMILES:** `CCCCCCCCCCCCCCCC(=O)NC(Cc1ccccc1)C(=O)O`
- **Best reported activity:** IC50 15 nM
- **ChEMBL assay:** ASSAY-DEMO-13
- **PubChem CID:** DEMO-103
- **Properties:** MW 612.4, XLogP 7.8, HBD 2, HBA 3, TPSA 66.4
- **Coarse screen:** CAUTION (2 Lipinski-style flags)
- **Rationale:** Potency-ranked candidate; requires selectivity, ADME, toxicity, and experimental validation.

### DEMO COMPOUND D (CHEMBL-DEMO-004)
- **SMILES:** `CN1CCN(CC1)c1ccc(NC(=O)c2ccccc2)cc1`
- **Best reported activity:** IC50 27.5 nM
- **ChEMBL assay:** ASSAY-DEMO-14
- **PubChem CID:** DEMO-104
- **Properties:** MW 295.4, XLogP 2.4, HBD 1, HBA 3, TPSA 35.6
- **Coarse screen:** PASS (0 Lipinski-style flags)
- **Rationale:** Potency-ranked candidate; requires selectivity, ADME, toxicity, and experimental validation.


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
