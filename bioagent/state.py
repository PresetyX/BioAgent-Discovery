"""Typed shared state and structured outputs for the discovery workflow."""

from __future__ import annotations

from typing import Any, Literal, TypedDict

from pydantic import BaseModel, Field


class TargetExtraction(BaseModel):
    """LLM-validated disease target extracted from retrieved literature."""

    target_protein: str = Field(description="Human-readable therapeutic protein target name")
    target_symbol: str = Field(description="Official or common gene/protein symbol")
    uniprot_id: str | None = Field(default=None, description="UniProt accession when evidenced")
    justification: str = Field(description="Concise evidence-based target rationale")
    confidence: Literal["HIGH", "MEDIUM", "LOW"]


class DiscoveryState(TypedDict, total=False):
    """Central state passed across LangGraph nodes."""

    disease: str
    disease_terms: list[str]
    literature: list[dict[str, Any]]
    target_protein: str | None
    target_symbol: str | None
    target_uniprot_id: str | None
    target_justification: str | None
    target_confidence: str | None
    target_chembl_id: str | None
    candidate_molecules: list[dict[str, Any]]
    screened_molecules: list[dict[str, Any]]
    final_report: str | None
    retry_count: int
    errors: list[str]
