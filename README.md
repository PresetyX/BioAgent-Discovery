# BioAgent-Discovery

AI-powered, multi-agent pipeline for early-stage drug-discovery research. It combines literature retrieval, target prioritization, bioactivity retrieval, and safety triage using public scientific APIs.

> **Research-use only.** This project does not provide clinical, therapeutic, or regulatory advice. All output must be reviewed and experimentally validated by qualified scientists.

## Architecture

```text
Disease input
    |
    v
Medical Literature Agent
  Europe PMC -> recent abstracts -> LLM structured target extraction
    |
    v
Chemoinformatics Agent
  ChEMBL -> target resolution -> IC50/Ki activities -> candidate ranking
    |
    v
Screener & Safety Agent
  PubChem -> physicochemical properties -> Lipinski screen -> Markdown report
```

The workflow is orchestrated by LangGraph and shares a typed central state between nodes. Nodes can route to controlled retry paths when a scientific API returns no usable data.

## Stack

- Python 3.10+
- LangGraph and LangChain
- OpenAI GPT-4o (default) or Anthropic Claude via LangChain
- Europe PMC, ChEMBL, and PubChem public APIs
- `requests`, `pandas`, Pydantic structured output

## Setup

```bash
git clone https://github.com/PresetyX/BioAgent-Discovery.git
cd BioAgent-Discovery
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
```

Set one provider key in `.env`:

```dotenv
OPENAI_API_KEY=your_key
OPENAI_MODEL=gpt-4o
# Optional alternative:
# ANTHROPIC_API_KEY=your_key
# ANTHROPIC_MODEL=claude-3-5-sonnet-latest
```

## Run

```bash
python main.py --disease "Alzheimer's disease" --output reports/alzheimer.md --verbose
```

The output is an English Markdown report with the proposed target, candidate molecules, potency metadata, available PubChem properties, safety flags, and explicit limitations.

## Reliability Design

- HTTP timeout, retry, and exponential backoff for every external API call
- Graceful error accumulation in LangGraph state
- Disease synonym retry for literature retrieval
- Pydantic schemas for LLM target extraction and final-report generation
- Numeric activity normalization to nM for reproducible compound ranking
- PubChem queries based on molecular SMILES, with manual-review status when resolution fails

## Scientific Limitations

- Literature-based target selection is hypothesis generation, not biological validation.
- ChEMBL activities vary by assay design, species, endpoint, and experimental context.
- Lipinski rules and public bioassay flags do not establish safety, ADME, selectivity, or clinical viability.
- The pipeline must never be used to select treatments, dose patients, or replace medicinal-chemistry, toxicology, or regulatory review.

## Project Layout

```text
bioagent/
  agents/       # Three agent nodes and prompts
  tools/        # Resilient clients for public scientific APIs
  graph.py      # LangGraph orchestration and retry routing
  state.py      # Shared typed state and schemas
main.py         # CLI
```

## License

MIT
