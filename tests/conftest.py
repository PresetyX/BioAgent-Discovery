"""Shared fixtures: fake HTTP sessions and canned API payloads (no network access)."""

from __future__ import annotations

from typing import Any

import pytest


class FakeResponse:
    def __init__(self, payload: Any = None, status_code: int = 200, text: str = "") -> None:
        self._payload = payload
        self.status_code = status_code
        self.text = text

    def json(self) -> Any:
        return self._payload

    def raise_for_status(self) -> None:
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")


class FakeSession:
    """Routes requests to canned responses by URL substring and records every call."""

    def __init__(self, routes: dict[str, FakeResponse]) -> None:
        self.routes = routes
        self.calls: list[tuple[str, str, dict[str, Any]]] = []

    def _match(self, method: str, url: str, **kwargs: Any) -> FakeResponse:
        self.calls.append((method, url, kwargs))
        for fragment, response in self.routes.items():
            if fragment in url:
                return response
        return FakeResponse(status_code=404)

    def get(self, url: str, **kwargs: Any) -> FakeResponse:
        return self._match("GET", url, **kwargs)

    def post(self, url: str, **kwargs: Any) -> FakeResponse:
        return self._match("POST", url, **kwargs)


@pytest.fixture
def fake_session():
    return FakeSession


@pytest.fixture
def fake_response():
    return FakeResponse


# --------------------------------------------------------------------------- canned data
EUROPE_PMC_PAYLOAD = {
    "resultList": {
        "result": [
            {
                "pmid": "DEMO-0001",
                "title": "BACE1 inhibition reduces amyloid-beta production (demo record)",
                "abstractText": "Demonstration abstract describing BACE1 as a therapeutic target.",
                "journalTitle": "Demo Journal",
                "firstPublicationDate": "2026-01-15",
            },
            {"pmid": "DEMO-0002", "title": "Record without abstract", "abstractText": ""},
        ]
    }
}

CHEMBL_TARGETS = {
    "_embedded": {
        "documents": [
            {"target_chembl_id": "CHEMBL-DEMO-T9", "organism": "Mus musculus", "target_type": "SINGLE PROTEIN"},
            {"target_chembl_id": "CHEMBL-DEMO-T1", "organism": "Homo sapiens", "target_type": "SINGLE PROTEIN"},
        ]
    }
}

CHEMBL_ACTIVITIES = {
    "_embedded": {
        "documents": [
            {"molecule_chembl_id": "CHEMBL-DEMO-A", "standard_type": "IC50", "standard_value": "40", "assay_chembl_id": "ASSAY-1"},
            {"molecule_chembl_id": "CHEMBL-DEMO-A", "standard_type": "Ki", "standard_value": "12", "assay_chembl_id": "ASSAY-2"},
            {"molecule_chembl_id": "CHEMBL-DEMO-B", "standard_type": "IC50", "standard_value": "3.5", "assay_chembl_id": "ASSAY-3"},
            {"molecule_chembl_id": "CHEMBL-DEMO-C", "standard_type": "IC50", "standard_value": "not-a-number"},
            {"molecule_chembl_id": "CHEMBL-DEMO-D", "standard_type": "IC50", "standard_value": "0"},
            {"molecule_chembl_id": "CHEMBL-DEMO-E", "standard_type": "IC50", "standard_value": "80", "assay_chembl_id": "ASSAY-4"},
        ]
    }
}

CHEMBL_MOLECULES = {
    "CHEMBL-DEMO-A": {"pref_name": "DEMO COMPOUND A", "molecule_structures": {"canonical_smiles": "CC(=O)Oc1ccccc1C(=O)O"}},
    "CHEMBL-DEMO-B": {"pref_name": None, "molecule_structures": {"canonical_smiles": "CN1C=NC2=C1C(=O)N(C(=O)N2C)C"}},
    "CHEMBL-DEMO-E": {"pref_name": "NO STRUCTURE", "molecule_structures": None},
}


def pubchem_properties(mw: float, xlogp: float, hbd: int, hba: int) -> dict[str, Any]:
    return {
        "PropertyTable": {
            "Properties": [
                {
                    "MolecularWeight": str(mw),
                    "XLogP": xlogp,
                    "HBondDonorCount": hbd,
                    "HBondAcceptorCount": hba,
                    "TPSA": 63.6,
                    "RotatableBondCount": 3,
                }
            ]
        }
    }
