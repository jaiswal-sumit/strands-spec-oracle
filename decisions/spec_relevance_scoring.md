# Reusable Decision Pattern: Spec Relevance Scoring

**Pattern type:** Context & Memory  
**Decider question type:** `score`  
**Tag:** `#context-memory`

---

## What it does

Before sending any spec content to a large language model, this pattern uses
Strands Decider 2B to score each spec chunk (0–2) for relevance to the
developer's question. Only chunks scoring above a configurable threshold
are forwarded to the LLM. Everything else is silently dropped.

This keeps the expensive model call focused and cheap. In a 50-chunk spec
corpus (~40k tokens), a typical question needs 3–6 chunks (~3k tokens),
saving ~92% of context tokens per query.

---

## The typed question

```json
{
  "state": "Developer question: {user_question}\n\nSpec file: {filename}\nSection: {heading}\n\n{chunk_text}",
  "questions": {
    "relevance": {
      "type": "score",
      "instructions": "How relevant is this spec section to answering the developer question above? 0 = completely irrelevant or from a different domain, 1 = somewhat related background info, 2 = directly answers or closely supports the question"
    }
  }
}
```

**Normalisation:** Decider returns a score on the 0–2 scale. Divide by 2 to
get a 0–1 value. Default threshold: `0.55` (i.e. raw score ≥ 1.1).

---

## Wiring into a Strands agent

### Option A — InterventionHandler (transparent, no tool needed)

```python
from spec_oracle.handlers import SpecContextInterventionHandler
from strands import Agent
from strands.models import BedrockModel

handler = SpecContextInterventionHandler(spec_dir="./specs")

agent = Agent(
    model=BedrockModel(model_id="us.anthropic.claude-3-5-haiku-20241022-v1:0"),
    system_prompt="Answer questions from the spec sections in your context.",
    interventions=[handler],
)

# The handler fires before_model_call, scores chunks, and injects
# only the relevant ones via Transform — the agent loop never sees
# the filtering happen.
response = agent("What is the retry strategy for failed payments?")

# Inspect what was filtered:
print(handler.last_filter_result.reduction_pct, "% tokens saved")
```

### Option B — Explicit tool call

```python
from spec_oracle.decider_client import score_and_filter
from spec_oracle.chunker import load_spec_directory

chunks = load_spec_directory("./specs")
result = score_and_filter(
    question="What is the retry strategy for failed payments?",
    chunks=chunks,
    threshold=0.55,
    max_chunks=6,
)

for sc in result.selected_chunks:
    print(f"[{sc.relevance:.2f}] {sc.chunk.file} › {sc.chunk.heading}")

# Pass result.selected_chunks to your LLM of choice
```

---

## Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `DECIDER_SERVER_URL` | `http://localhost:8000` | URL of the running Decider 2B server |
| `RELEVANCE_THRESHOLD` | `0.55` | Normalised score cutoff (0–1) |
| `MAX_CONTEXT_CHUNKS` | `6` | Hard cap on chunks sent to LLM |

---

## Starting the Decider server

```bash
pip install strands-decider
strands-decider serve StrandsAgents/strands-decider-2B-hobson-v19 --port 8000
```

The server stays warm between requests, so the model is loaded once and each
question costs only ~115ms regardless of corpus size.

---

## When to use this pattern

Use it whenever your agent has a large static knowledge base (docs, specs,
runbooks, policies) and you want to avoid stuffing the entire corpus into
context on every call. It works best when:

- The corpus is split into clearly scoped sections (one topic per heading)
- Questions are specific enough that only a few sections are truly relevant
- You want measurable, auditable context decisions (not just semantic search)

---

## Accuracy notes

At a threshold of 0.55, Decider 2B's calibration means answers at that
confidence level are correct ~75–80% of the time. For mission-critical
spec queries, lower the threshold to 0.35 and accept slightly more noise,
or raise it to 0.70 for higher precision at the cost of recall.

See the [Decider 2B evaluation](https://github.com/strands-labs/strands-decider/blob/main/evaluation/results.md) for full calibration data.
