# Polza in CustDev

CustDev uses the same `POLZA_API_KEY` and `POLZA_API_BASE` configuration
convention as the main Pitchy project. Provider: `https://polza.ai/api/v1`.
The key must be supplied privately through the deployment environment.
There is no fallback to RouterAI, Ollama, or a default OpenAI endpoint.

Approved model assignments:

| Task | Model | Optional override |
|---|---|---|
| Search-query planning | deepseek/deepseek-v4-flash | CUSTDEV_MODEL_SEARCH |
| Market signals | openai/gpt-6-luna-pro | CUSTDEV_MODEL_SIGNALS |
| Ontology | openai/gpt-6-luna-pro | CUSTDEV_MODEL_ONTOLOGY |
| Entity/relation extraction | deepseek/deepseek-v4-flash | CUSTDEV_MODEL_EXTRACTION |
| Respondent profiles | openai/gpt-6-luna | CUSTDEV_MODEL_PROFILES |
| Simulation settings | deepseek/deepseek-v4-flash | CUSTDEV_MODEL_SIMULATION_CONFIG |
| Simulation and interviews | openai/gpt-6-luna | CUSTDEV_MODEL_SIMULATION |
| Graph analysis | openai/gpt-6-luna-pro | CUSTDEV_MODEL_GRAPH_ANALYSIS |
| Report generation | openai/gpt-6-luna-pro | CUSTDEV_MODEL_REPORT |
| Final verdict | openai/gpt-6-luna-pro | CUSTDEV_MODEL_VERDICT |
| Report chat | openai/gpt-6-luna | CUSTDEV_MODEL_REPORT_CHAT |
| Embeddings | qwen/qwen3-embedding-8b | POLZA_EMBEDDING_MODEL |

`backend/llm_settings.py` supplies these defaults to Flask and all three
standalone OASIS launchers. It replaces legacy `LLM_*`, `LLM_BOOST_*`,
`OPENAI_*`, and `EMBEDDING_*` environment aliases with the Polza settings.
Worker factories also pass the URL and key explicitly to CAMEL, so old
saved simulation settings cannot select a different provider.

Embeddings use authenticated batch requests with `dimensions=768` and
`encoding_format=float`, matching the existing Neo4j indexes. Old graph
vectors must be re-embedded when changing models: identical dimensions do
not make vectors from different models comparable. Preserve a backup
before replacing historical vectors; do not delete the graphs or uploads.

Validation from `backend/`:

```text
python -m pytest tests -q
python scripts/check_polza.py
python scripts/check_camel_polza.py
```

The second command makes small paid calls to all three chat models and the
embedding model. It checks structured JSON and batch-vector dimensions;
it does not run a full customer-development study.
The third command verifies a real CAMEL tool call using the simulation model.
