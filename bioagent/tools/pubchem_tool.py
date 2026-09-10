"""PubChem PUG REST client for physicochemical screening data."""

from __future__ import annotations

from typing import Any

import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

PUBCHEM_PUG_URL = "https://pubchem.ncbi.nlm.nih.gov/rest/pug"


def _session() -> requests.Session:
    """Create a retry-enabled PubChem HTTP client."""
    session = requests.Session()
    retry = Retry(total=3, backoff_factor=0.6, status_forcelist=(429, 500, 502, 503, 504), allowed_methods=("GET", "POST"))
    session.mount("https://", HTTPAdapter(max_retries=retry))
    return session


def screen_smiles(smiles: str) -> dict[str, Any]:
    """Resolve SMILES to a PubChem CID and evaluate Lipinski-style flags.

    This is a coarse prioritization screen, not a toxicity prediction or safety claim.
    """
    cid_response = _session().post(f"{PUBCHEM_PUG_URL}/compound/smiles/cid/TXT", data={"smiles": smiles}, timeout=25)
    cid_response.raise_for_status()
    cid = cid_response.text.strip().splitlines()[0]
    properties = "MolecularWeight,XLogP,HBondDonorCount,HBondAcceptorCount,TPSA,RotatableBondCount"
    response = _session().get(f"{PUBCHEM_PUG_URL}/compound/cid/{cid}/property/{properties}/JSON", timeout=25)
    response.raise_for_status()
    data = response.json()["PropertyTable"]["Properties"][0]
    mw = float(data.get("MolecularWeight", 0))
    xlogp = float(data.get("XLogP", 0))
    hbd = int(data.get("HBondDonorCount", 0))
    hba = int(data.get("HBondAcceptorCount", 0))
    flags = []
    if mw > 500:
        flags.append("Molecular weight > 500")
    if xlogp > 5:
        flags.append("XLogP > 5")
    if hbd > 5:
        flags.append("Hydrogen-bond donors > 5")
    if hba > 10:
        flags.append("Hydrogen-bond acceptors > 10")
    return {
        "pubchem_cid": cid,
        "molecular_weight": mw,
        "xlogp": xlogp,
        "hbd": hbd,
        "hba": hba,
        "tpsa": float(data.get("TPSA", 0)),
        "rotatable_bonds": int(data.get("RotatableBondCount", 0)),
        "lipinski_violations": len(flags),
        "flags": flags,
        "screening_status": "REJECT" if len(flags) > 2 else "CAUTION" if len(flags) == 2 else "PASS",
    }
