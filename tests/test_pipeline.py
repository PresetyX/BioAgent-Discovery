"""Unit and integration tests for the BioAgent-Discovery pipeline.

Every external dependency (Europe PMC, ChEMBL, PubChem and the LLM) is replaced by a
deterministic fake, so the suite runs offline and in CI without API keys.
"""

from __future__ import annotations

import pytest

from bioagent import graph as graph_module
from bioagent.agents import chemoinformatics_agent, medical_agent, screener_agent
from bioagent.state import TargetExtraction
from bioagent.tools import chembl_tool, pubchem_tool, pubmed_tool
from tests.conftest import (
    CHEMBL_ACTIVITIES,
    CHEMBL_MOLECULES,
    CHEMBL_TARGETS,
    EUROPE_PMC_PAYLOAD,
    FakeResponse,
    FakeSession,
    pubchem_properties,
)


# =========================================================================== tools
class TestEuropePMC:
    def test_search_builds_query_and_drops_records_without_abstract(self, monkeypatch):
        session = FakeSession({"europepmc": FakeResponse(EUROPE_PMC_PAYLOAD)})
        monkeypatch.setattr(pubmed_tool, "_session", lambda: session)

        records = pubmed_tool.search_literature("Alzheimer's disease", limit=5)

        assert [r["pmid"] for r in records] == ["DEMO-0001"]
        assert records[0]["journal"] == "Demo Journal"
        params = session.calls[0][2]["params"]
        assert '"Alzheimer\'s disease"' in params["query"]
        assert params["pageSize"] == 5
        assert session.calls[0][2]["timeout"] == 25

    def test_search_returns_empty_list_when_no_results(self, monkeypatch):
        session = FakeSession({"europepmc": FakeResponse({"resultList": {}})})
        monkeypatch.setattr(pubmed_tool, "_session", lambda: session)
        assert pubmed_tool.search_literature("unknown") == []

    def test_search_propagates_http_errors(self, monkeypatch):
        session = FakeSession({"europepmc": FakeResponse(status_code=503)})
        monkeypatch.setattr(pubmed_tool, "_session", lambda: session)
        with pytest.raises(RuntimeError, match="503"):
            pubmed_tool.search_literature("x")


class TestChEMBL:
    def test_find_target_prefers_human_single_protein(self, monkeypatch):
        session = FakeSession({"target/search": FakeResponse(CHEMBL_TARGETS)})
        monkeypatch.setattr(chembl_tool, "_session", lambda: session)
        assert chembl_tool.find_target("BACE1")["target_chembl_id"] == "CHEMBL-DEMO-T1"

    def test_find_target_returns_none_when_empty(self, monkeypatch):
        session = FakeSession({"target/search": FakeResponse({"_embedded": {"documents": []}})})
        monkeypatch.setattr(chembl_tool, "_session", lambda: session)
        assert chembl_tool.find_target("nothing") is None

    def test_ranked_compounds_dedupe_sort_and_skip_invalid(self, monkeypatch):
        routes = {"activity.json": FakeResponse(CHEMBL_ACTIVITIES)}
        for chembl_id, payload in CHEMBL_MOLECULES.items():
            routes[f"molecule/{chembl_id}.json"] = FakeResponse(payload)
        session = FakeSession(routes)
        monkeypatch.setattr(chembl_tool, "_session", lambda: session)

        compounds = chembl_tool.get_ranked_compounds("CHEMBL-DEMO-T1", limit=5)

        # B (3.5 nM) before A (best of 40 and 12 nM -> 12). C (not numeric) and D (0 nM) are
        # discarded; E has no SMILES and is skipped.
        assert [c["chembl_id"] for c in compounds] == ["CHEMBL-DEMO-B", "CHEMBL-DEMO-A"]
        assert compounds[1]["activity_value_nm"] == 12
        assert compounds[1]["activity_type"] == "Ki"
        assert compounds[0]["compound_name"] == "CHEMBL-DEMO-B"  # falls back to the ID
        assert compounds[1]["compound_name"] == "DEMO COMPOUND A"

    def test_ranked_compounds_respects_limit(self, monkeypatch):
        routes = {"activity.json": FakeResponse(CHEMBL_ACTIVITIES)}
        for chembl_id, payload in CHEMBL_MOLECULES.items():
            routes[f"molecule/{chembl_id}.json"] = FakeResponse(payload)
        monkeypatch.setattr(chembl_tool, "_session", lambda: FakeSession(routes))
        assert len(chembl_tool.get_ranked_compounds("T", limit=1)) == 1


class TestPubChem:
    @pytest.mark.parametrize(
        ("props", "violations", "status"),
        [
            ((180.2, 1.2, 1, 4), 0, "PASS"),
            ((620.0, 5.8, 2, 6), 2, "CAUTION"),
            ((720.0, 6.5, 7, 12), 4, "REJECT"),
        ],
    )
    def test_lipinski_screen(self, monkeypatch, props, violations, status):
        session = FakeSession(
            {
                "smiles/cid/TXT": FakeResponse(text="2244\n"),
                "cid/2244/property": FakeResponse(pubchem_properties(*props)),
            }
        )
        monkeypatch.setattr(pubchem_tool, "_session", lambda: session)

        result = pubchem_tool.screen_smiles("CC(=O)Oc1ccccc1C(=O)O")

        assert result["pubchem_cid"] == "2244"
        assert result["lipinski_violations"] == violations
        assert result["screening_status"] == status
        assert session.calls[0][0] == "POST"  # SMILES is sent in the body, not the URL


# =========================================================================== agents
class FakeExtractor:
    def __init__(self, result: TargetExtraction | Exception) -> None:
        self.result = result
        self.messages = None

    def invoke(self, messages):
        self.messages = messages
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


class FakeLLM:
    def __init__(self, extractor: FakeExtractor) -> None:
        self.extractor = extractor

    def with_structured_output(self, schema):
        assert schema is TargetExtraction
        return self.extractor


TARGET = TargetExtraction(
    target_protein="Beta-secretase 1",
    target_symbol="BACE1",
    uniprot_id="P56817",
    justification="Demo rationale based on the fake abstract.",
    confidence="MEDIUM",
)


class TestMedicalAgent:
    def test_uses_first_term_with_results_and_extracts_target(self, monkeypatch):
        calls = []

        def fake_search(term):
            calls.append(term)
            return [] if term == "alz" else [{"pmid": "1", "title": "T", "abstract": "A" * 5000}]

        extractor = FakeExtractor(TARGET)
        monkeypatch.setattr(medical_agent, "search_literature", fake_search)
        monkeypatch.setattr(medical_agent, "_llm", lambda: FakeLLM(extractor))

        result = medical_agent.medical_literature_node(
            {"disease": "alz", "disease_terms": ["alz", "alz disease"], "errors": []}
        )

        assert calls == ["alz", "alz disease"]  # synonym retry
        assert result["target_symbol"] == "BACE1"
        assert result["target_confidence"] == "MEDIUM"
        human_prompt = extractor.messages[1][1]
        assert "Retrieved term: alz disease" in human_prompt
        assert "A" * 2201 not in human_prompt  # abstracts are truncated to 2200 chars

    def test_records_errors_when_every_search_fails(self, monkeypatch):
        def boom(term):
            raise ConnectionError("offline")

        monkeypatch.setattr(medical_agent, "search_literature", boom)
        result = medical_agent.medical_literature_node({"disease": "x", "disease_terms": ["x"], "errors": []})
        assert result["target_protein"] is None
        assert "Europe PMC search failed for 'x': offline" in result["errors"]
        assert "No usable literature abstracts were retrieved." in result["errors"]

    def test_llm_failure_is_captured(self, monkeypatch):
        monkeypatch.setattr(medical_agent, "search_literature", lambda t: [{"title": "T", "abstract": "A"}])
        monkeypatch.setattr(medical_agent, "_llm", lambda: FakeLLM(FakeExtractor(ValueError("bad json"))))
        result = medical_agent.medical_literature_node({"disease": "x", "disease_terms": ["x"], "errors": []})
        assert result["target_protein"] is None
        assert result["errors"] == ["Target extraction failed: bad json"]


class TestChemoinformaticsAgent:
    def test_falls_back_through_target_identifiers(self, monkeypatch):
        tried = []

        def fake_find(term):
            tried.append(term)
            if term == "BACE1":
                raise TimeoutError("slow")
            return {"target_chembl_id": "CHEMBL-DEMO-T1"} if term == "P56817" else None

        monkeypatch.setattr(chemoinformatics_agent, "find_target", fake_find)
        monkeypatch.setattr(chemoinformatics_agent, "get_ranked_compounds", lambda tid, limit: [{"chembl_id": "X"}])

        result = chemoinformatics_agent.chemoinformatics_node(
            {"target_symbol": "BACE1", "target_protein": "Beta-secretase 1", "target_uniprot_id": "P56817", "errors": []}
        )

        assert tried == ["BACE1", "Beta-secretase 1", "P56817"]
        assert result["target_chembl_id"] == "CHEMBL-DEMO-T1"
        assert result["candidate_molecules"] == [{"chembl_id": "X"}]
        assert "ChEMBL target lookup failed for 'BACE1': slow" in result["errors"]

    def test_unresolved_target(self, monkeypatch):
        monkeypatch.setattr(chemoinformatics_agent, "find_target", lambda term: None)
        result = chemoinformatics_agent.chemoinformatics_node({"target_symbol": "ZZZ", "errors": []})
        assert result["candidate_molecules"] == []
        assert "Target could not be resolved in ChEMBL." in result["errors"]


COMPOUND = {
    "chembl_id": "CHEMBL-DEMO-A",
    "compound_name": "DEMO COMPOUND A",
    "smiles": "CCO",
    "activity_type": "IC50",
    "activity_value_nm": 12.0,
    "assay_chembl_id": "ASSAY-1",
}


class TestScreenerAgent:
    def test_report_excludes_rejected_and_flags_manual_review(self, monkeypatch):
        def fake_screen(smiles):
            if smiles == "BAD":
                return {"screening_status": "REJECT", "lipinski_violations": 4}
            if smiles == "ERR":
                raise ConnectionError("pubchem down")
            return {"screening_status": "PASS", "lipinski_violations": 0, "pubchem_cid": "1"}

        monkeypatch.setattr(screener_agent, "screen_smiles", fake_screen)
        state = {
            "disease": "Demo disease",
            "target_protein": "Beta-secretase 1",
            "target_symbol": "BACE1",
            "candidate_molecules": [
                COMPOUND,
                {**COMPOUND, "chembl_id": "REJ", "compound_name": "REJECTED ONE", "smiles": "BAD"},
                {**COMPOUND, "chembl_id": "ERR-1", "compound_name": "ERRORED ONE", "smiles": "ERR"},
            ],
            "errors": [],
        }

        result = screener_agent.screening_node(state)
        report = result["final_report"]

        assert len(result["screened_molecules"]) == 3
        assert "**Candidates screened:** 3" in report
        assert "**Candidates retained:** 2" in report
        assert "DEMO COMPOUND A" in report
        assert "REJECTED ONE" not in report
        assert "MANUAL REVIEW" in report
        assert result["errors"] == ["PubChem screen failed for ERR-1: pubchem down"]
        for section in ("## Executive Summary", "## Methodology", "## Limitations"):
            assert section in report


# =========================================================================== graph
class TestGraph:
    def test_routing_functions(self):
        assert graph_module._after_medical({"target_protein": "X"}) == "chemoinformatics"
        assert graph_module._after_medical({}) == "finish"
        assert graph_module._after_chemistry({"candidate_molecules": [{}]}) == "screening"
        assert graph_module._after_chemistry({"candidate_molecules": []}) == "finish"

    def test_finish_node_writes_error_report(self):
        out = graph_module._finish_node({"errors": ["boom"]})
        assert "stopped before candidate screening" in out["final_report"]
        assert "- boom" in out["final_report"]

    def test_full_pipeline_end_to_end_with_fakes(self, monkeypatch):
        monkeypatch.setattr(
            medical_agent,
            "search_literature",
            lambda term: [{"pmid": "DEMO-0001", "title": "Demo title", "abstract": "Demo abstract"}],
        )
        monkeypatch.setattr(medical_agent, "_llm", lambda: FakeLLM(FakeExtractor(TARGET)))
        monkeypatch.setattr(chemoinformatics_agent, "find_target", lambda term: {"target_chembl_id": "T1"})
        monkeypatch.setattr(chemoinformatics_agent, "get_ranked_compounds", lambda tid, limit: [COMPOUND])
        monkeypatch.setattr(
            screener_agent, "screen_smiles", lambda s: {"screening_status": "PASS", "lipinski_violations": 0}
        )

        state = graph_module.run_pipeline("Alzheimer's disease")

        assert state["disease_terms"][0] == "Alzheimer's disease"
        assert state["target_chembl_id"] == "T1"
        assert "Beta-secretase 1 (BACE1)" in state["final_report"]
        assert "PMID DEMO-0001: Demo title" in state["final_report"]
        assert state["errors"] == []

    def test_pipeline_stops_gracefully_without_literature(self, monkeypatch):
        monkeypatch.setattr(medical_agent, "search_literature", lambda term: [])
        state = graph_module.run_pipeline("unknown disease")
        assert "stopped before candidate screening" in state["final_report"]
        assert "candidate_molecules" not in state
