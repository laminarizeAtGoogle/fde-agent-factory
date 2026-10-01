# Model Migration Report: GPT-4o -> Gemini 2.5 Pro

## 1. Executive Summary
- **Migration Path**: OpenAI GPT-4o (Legacy) -> Gemini 2.5 Pro (Target).
- **Effort Score**: Medium.
- **Key Benefit**: Dramatic simplification of the RAG pipeline by leveraging Gemini's 2M context window.

## 2. Capability Comparison

| Feature | GPT-4o | Gemini 2.5 Pro | Impact |
| :--- | :--- | :--- | :--- |
| **Context Window** | 128,000 | 2,000,000 | **High**: Can ingest full codebases. |
| **Multimodal** | Yes (Vision) | Yes (Audio/Video/Doc) | **Medium**: Native PDF support. |
| **Grounding** | Custom / Perplexity | Native (Google Search) | **High**: Remove custom search tools. |
| **SDK** | `openai` | `google-genai` | **Low**: Structural mapping required. |

## 3. Code-Level Changes

### Initialization (src/client.py)
**Old (OpenAI):**
```python
from openai import OpenAI
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])
```

**New (Gemini SDK):**
```python
from google import genai
client = genai.Client(api_key=os.environ["GEMINI_API_KEY"])
```

### Tool Definition Mapping
OpenAI uses `functions` or `tools`, whereas Gemini 2.5 SDK prefer direct Python function passing or `tools=[search_tool]`.

**Legacy (JSON Schema):**
```python
{"name": "get_weather", "parameters": {...}}
```

**Target (Native Python):**
```python
def get_weather(location: str):
    """Fetches weather for a location."""
    ...
```

## 4. Optimization Roadmap
1.  **Eliminate Vector DB Reranking**: The current `HNSW` + `Rerank` loop in `src/rag/search.py` is necessary for GPT-4o's 128k limit. Moving to Gemini allows passing the Top-50 documents (up to 1M tokens) directly, improving recall accuracy.
2.  **Native Search Grounding**: Replace the `Tavily` tool in `src/tools/web.py` with `google_search_retrieval` for lower latency and better integration.
3.  **Thinking Config**: Replace the manual "Think step by step" prefix in `prompts/instruction.txt` with Gemini's `thinking_config` for better low-latency reasoning.

## 5. Risk Audit & Verification
- **Risk**: Structured output consistency for deeply nested JSON objects may vary slightly between models.
- **Verification**: Run `uv run pytest tests/model_parity_tests.py` using the `response_schema` validation logic.
