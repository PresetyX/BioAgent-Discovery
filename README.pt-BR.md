🌐 [English](README.md) | **Português (BR)**

# BioAgent-Discovery

[![CI](https://github.com/PresetyX/BioAgent-Discovery/actions/workflows/ci.yml/badge.svg)](https://github.com/PresetyX/BioAgent-Discovery/actions/workflows/ci.yml)
![Python](https://img.shields.io/badge/python-3.10%20%7C%203.12-blue)
![License](https://img.shields.io/badge/license-MIT-green)

Pipeline multiagente com IA para pesquisa em estágio inicial de descoberta de fármacos. Combina busca de literatura, priorização de alvos, obtenção de bioatividade e triagem de segurança usando APIs científicas públicas.

> **Somente para uso em pesquisa.** Este projeto não oferece orientação clínica, terapêutica ou regulatória. Toda saída deve ser revisada e validada experimentalmente por cientistas qualificados.

## Arquitetura

```text
Doença (entrada)
    |
    v
Agente de Literatura Médica
  Europe PMC -> resumos recentes -> extração estruturada de alvos por LLM
    |
    v
Agente de Quimioinformática
  ChEMBL -> resolução do alvo -> atividades IC50/Ki -> ranking de candidatos
    |
    v
Agente de Triagem e Segurança
  PubChem -> propriedades físico-químicas -> triagem de Lipinski -> relatório em Markdown
```

O fluxo é orquestrado pelo LangGraph e compartilha um estado central tipado entre os nós. Os nós podem seguir para caminhos de nova tentativa controlados quando uma API científica não retorna dados utilizáveis.

## Stack

- Python 3.10+
- LangGraph e LangChain
- OpenAI GPT-4o (padrão) ou Anthropic Claude via LangChain
- APIs públicas Europe PMC, ChEMBL e PubChem
- `requests`, `pandas`, saída estruturada com Pydantic

## Configuração

```bash
git clone https://github.com/PresetyX/BioAgent-Discovery.git
cd BioAgent-Discovery
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\\Scripts\\activate
pip install -r requirements.txt
cp .env.example .env
```

Defina a chave de um provedor no `.env`:

```dotenv
OPENAI_API_KEY=sua_chave
OPENAI_MODEL=gpt-4o
# Alternativa opcional:
# ANTHROPIC_API_KEY=sua_chave
# ANTHROPIC_MODEL=claude-3-5-sonnet-latest
```

## Execução

```bash
python main.py --disease "Alzheimer's disease" --output reports/alzheimer.md --verbose
```

A saída é um relatório em Markdown, em inglês, com o alvo proposto, as moléculas candidatas, metadados de potência, as propriedades disponíveis no PubChem, alertas de segurança e limitações explícitas.

Veja [`sample_report.md`](sample_report.md) para o formato do relatório. Ele é produzido rodando o pipeline real com respostas de API simuladas (`python scripts/generate_sample_report.py`), então todos os identificadores e valores nele são sintéticos.

### Docker

```
docker build -t bioagent-discovery .
docker run --rm -e OPENAI_API_KEY=sua_chave -v "$PWD/reports:/app/reports" bioagent-discovery \
  --disease "Alzheimer's disease" --output reports/alzheimer.md
```

## Testes

```
pip install -r requirements-dev.txt
pytest --cov=bioagent
```

A suíte (20 testes, ~92% de cobertura) roda totalmente offline: Europe PMC, ChEMBL, PubChem e o LLM são substituídos por simulações determinísticas. Ela cobre a construção de consultas, o filtro de registros, a remoção de duplicatas de potência e o ranking no ChEMBL, os limites PASS / CAUTION / REJECT no estilo Lipinski, a nova tentativa com sinônimos e o acúmulo de erros em cada agente, o roteamento do LangGraph e uma execução de ponta a ponta do grafo compilado.

O GitHub Actions roda o lint (ruff), os testes em Python 3.10 e 3.12, verifica que o `sample_report.md` é reproduzível e faz o build da imagem Docker.

## Design de confiabilidade

- Timeout HTTP, nova tentativa e backoff exponencial em toda chamada a API externa
- Acúmulo gracioso de erros no estado do LangGraph
- Nova tentativa com sinônimos da doença na busca de literatura
- Schemas Pydantic para a extração de alvos pelo LLM e para a geração do relatório final
- Normalização numérica das atividades para nM, para um ranking de compostos reproduzível
- Consultas ao PubChem baseadas em SMILES moleculares, com status de revisão manual quando a resolução falha

## Decisões de design

- **Um grafo sequencial com proteções, em vez de agentes soltos.** As três etapas sempre rodam
  em ordem, e cada transição confere se a etapa anterior produziu o que a próxima precisa
  (um alvo para a química, candidatos para a triagem). Quando não produziu, um nó `finish` escreve
  um relatório controlado com os erros registrados, em vez de falhar adiante.
- **Um único estado compartilhado e tipado.** `DiscoveryState` é o único lugar onde ficam os
  resultados das etapas e os erros acumulados, então uma etapa pode falhar sem perder o que as
  anteriores encontraram.
- **O LLM não devolve texto livre onde uma decisão depende dele.** A extração de alvo passa por
  um schema Pydantic (proteína, símbolo, UniProt id somente quando há evidência, justificativa e
  uma confiança ALTA/MÉDIA/BAIXA — HIGH/MEDIUM/LOW), então a escolha do alvo é validada e traz a sua justificativa.
- **APIs externas são tratadas como não confiáveis.** As chamadas ao ChEMBL e ao PubChem usam uma
  política de nova tentativa com backoff exponencial em respostas 429 e 5xx e um timeout explícito, e as falhas são
  registradas no estado em vez de lançadas como exceção.
- **A busca de literatura tenta de novo com o nome da doença e duas variantes** (`<doença> disease`,
  `<doença> pathology`) antes de desistir.
- **Candidatos são ranqueados em uma única unidade.** As atividades IC50 e Ki são normalizadas para nM, para que o
  ranking seja reproduzível, e o PubChem é consultado por SMILES; quando uma molécula não pode ser resolvida,
  ela é marcada para revisão manual em vez de ser descartada em silêncio.
- **O escopo também está declarado no relatório gerado.** O agente de triagem acrescenta uma nota de que o
  relatório é um artefato de priorização de pesquisa, não evidência de eficácia ou segurança; veja as
  limitações abaixo.

## Limitações científicas

- A seleção de alvos baseada em literatura é geração de hipóteses, não validação biológica.
- As atividades do ChEMBL variam conforme o desenho do ensaio, a espécie, o desfecho e o contexto experimental.
- As regras de Lipinski e os alertas de bioensaios públicos não estabelecem segurança, ADME, seletividade nem viabilidade clínica.
- O pipeline nunca deve ser usado para escolher tratamentos, dosar pacientes ou substituir a revisão de química medicinal, toxicologia ou regulatória.

## Estrutura do projeto

```text
bioagent/
  agents/       # Três nós de agente e prompts
  tools/        # Clientes resilientes para APIs científicas públicas
  graph.py      # Orquestração do LangGraph e roteamento de novas tentativas
  state.py      # Estado compartilhado tipado e schemas
main.py         # CLI
scripts/        # gerador do relatório de exemplo
tests/          # suíte pytest offline
```

## Histórico de desenvolvimento

Este projeto foi desenvolvido localmente entre 10/09/2026 e 17/11/2026. O histórico de commits foi criado depois, e as datas dos commits foram ajustadas para corresponder ao período em que o trabalho foi realmente feito.

## Licença

MIT
