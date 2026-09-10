"""Medical literature agent node."""

from __future__ import annotations

import os

from langchain_anthropic import ChatAnthropic
from langchain_openai import ChatOpenAI

from bioagent.state import DiscoveryState, TargetExtraction
from bioagent.tools.pubmed_tool import search_literature

SYSTEM_PROMPT = """You are the Medical Literature Agent in a drug-discovery research workflow.
Use only the retrieved abstracts supplied by the user as evidence. Identify one therapeutically actionable protein target most associated with the disease mechanism. Do not invent identifiers, claims, or references. If the evidence is insufficient, select the best-supported target and mark confidence LOW. Output the required structured schema."""


def _llm():
    """Choose a configured LangChain chat model."""
    if os.getenv("ANTHROPIC_API_KEY"):
        return ChatAnthropic(model=os.getenv("ANTHROPIC_MODEL", "claude-3-5-sonnet-latest"), temperature=0)
    return ChatOpenAI(model=os.getenv("OPENAI_MODEL", "gpt-4o"), temperature=0)


def medical_literature_node(state: DiscoveryState) -> DiscoveryState:
    """Retrieve literature and use structured LLM output to select a target."""
    errors = list(state.get("errors", []))
    literature = []
    used_term = None
    for term in state.get("disease_terms", [state["disease"]]):
        try:
            literature = search_literature(term)
            if literature:
                used_term = term
                break
        except Exception as exc:
            errors.append(f"Europe PMC search failed for '{term}': {exc}")
    if not literature:
        return {"literature": [], "errors": errors + ["No usable literature abstracts were retrieved."], "target_protein": None}
    context = "\n\n".join(
        f"PMID: {item.get('pmid', 'N/A')}\nTitle: {item['title']}\nAbstract: {item['abstract'][:2200]}"
        for item in literature[:6]
    )
    try:
        extractor = _llm().with_structured_output(TargetExtraction)
        target = extractor.invoke([
            ("system", SYSTEM_PROMPT),
            ("human", f"Disease: {state['disease']}\nRetrieved term: {used_term}\n\nAbstracts:\n{context}"),
        ])
        return {
            "literature": literature,
            "target_protein": target.target_protein,
            "target_symbol": target.target_symbol,
            "target_uniprot_id": target.uniprot_id,
            "target_justification": target.justification,
            "target_confidence": target.confidence,
            "errors": errors,
        }
    except Exception as exc:
        return {"literature": literature, "errors": errors + [f"Target extraction failed: {exc}"], "target_protein": None}
