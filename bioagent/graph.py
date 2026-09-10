"""LangGraph orchestration for the BioAgent-Discovery workflow."""

from __future__ import annotations

from langgraph.graph import END, START, StateGraph

from bioagent.agents.chemoinformatics_agent import chemoinformatics_node
from bioagent.agents.medical_agent import medical_literature_node
from bioagent.agents.screener_agent import screening_node
from bioagent.state import DiscoveryState


def _after_medical(state: DiscoveryState) -> str:
    """Route to chemistry only when target extraction succeeded."""
    return "chemoinformatics" if state.get("target_protein") else "finish"


def _after_chemistry(state: DiscoveryState) -> str:
    """Route to screening only when candidates exist."""
    return "screening" if state.get("candidate_molecules") else "finish"


def _finish_node(state: DiscoveryState) -> DiscoveryState:
    """Produce a controlled report when upstream stages cannot continue."""
    if state.get("final_report"):
        return {}
    return {
        "final_report": "# BioAgent-Discovery Report\n\nThe workflow stopped before candidate screening. Review the recorded errors and retry with a more specific disease term.\n\n## Errors\n" + "\n".join(f"- {e}" for e in state.get("errors", []))
    }


def build_graph():
    """Build the sequential LangGraph workflow with guarded transitions."""
    graph = StateGraph(DiscoveryState)
    graph.add_node("medical_literature", medical_literature_node)
    graph.add_node("chemoinformatics", chemoinformatics_node)
    graph.add_node("screening", screening_node)
    graph.add_node("finish", _finish_node)
    graph.add_edge(START, "medical_literature")
    graph.add_conditional_edges("medical_literature", _after_medical, {"chemoinformatics": "chemoinformatics", "finish": "finish"})
    graph.add_conditional_edges("chemoinformatics", _after_chemistry, {"screening": "screening", "finish": "finish"})
    graph.add_edge("screening", END)
    graph.add_edge("finish", END)
    return graph.compile()


def run_pipeline(disease: str) -> DiscoveryState:
    """Run the discovery pipeline for a disease and common fallback terms."""
    terms = [disease, f"{disease} disease", f"{disease} pathology"]
    initial: DiscoveryState = {"disease": disease, "disease_terms": list(dict.fromkeys(terms)), "retry_count": 0, "errors": []}
    return build_graph().invoke(initial)
