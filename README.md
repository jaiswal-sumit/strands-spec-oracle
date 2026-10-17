# Strands Spec Oracle

![Spec Oracle](spec-oracle.png)

**SDD spec querying with Decider 2B context scoring + Amazon Bedrock**

> Hackathon submission for the [Strands Decider 2B Hackathon](https://builder.aws.com/build/hackathons/4f50957c-1d08-37ab-b11c-97516b9adeb4/agent-experience-hackathon-strands-decider)
> Decision pattern: **Context & Memory** (`#context-memory`)

---

## What it does

Software teams doing Spec-Driven Development accumulate dozens of markdown spec
files — API contracts, data models, auth flows, error handling policies. When a
developer asks *"what's the retry strategy for failed payments?"*, today they grep
manually or dump everything into an LLM and burn tokens.

**Spec Oracle** fixes this. Before a single token reaches Amazon Bedrock, Strands
Decider 2B scores every spec chunk for relevance in ~115ms each. Only the
top-scoring chunks go into context. The result: precise, cited answers using a
fraction of the tokens.

```
Developer: "What's the retry strategy for failed payments?"
                          │
              ┌───────────▼───────────┐
              │  Strands Decider 2B   │  scores 313 chunks in ~36s
              │  (context scoring)    │  keeps 4, drops 309
              └───────────┬───────────┘
                          │  ~802 tokens  (saved ~24,038 tokens, 97%)
              ┌───────────▼───────────┐
              │   Amazon Bedrock      │  generates cited answer
              │   (Claude Haiku)      │
              └───────────┬───────────┘
                          │
              "Per [15-idempotency-and-retries.md › Retriable vs Non-Retriable],
               retry on 429/5xx with exponential backoff. Always include
               Idempotency-Key on retried POSTs. 4xx client errors are
               not retriable. Max 4 attempts with jitter."
```

---

## Quick start

### Prerequisites

- Python 3.10+
- AWS credentials with Bedrock access (`us-east-1` or your preferred region)
- A GPU or Apple Silicon Mac to run Decider 2B locally (or CPU, slower)

### Install

```bash
git clone https://github.com/jaiswal-sumit/strands-spec-oracle
cd strands-spec-oracle
pip install -r requirements.txt
cp .env.example .env   # edit AWS region / model if needed
```

### Start the Decider 2B server

In a separate terminal:

```bash
pip install strands-decider
strands-decider serve StrandsAgents/strands-decider-2B-hobson-v19 --port 8000
```

### Run the agent

```bash
# Interactive mode
python -m spec_oracle.agent --specs ./demo/specs

# Single question (non-interactive)
python -m spec_oracle.agent --specs ./demo/specs \
  -q "What HTTP status code is returned when a rate limit is exceeded?"

# Point at your own SDD spec directory
python -m spec_oracle.agent --specs /path/to/your/specs
```

### Using APM

```bash
npm install -g @microsoft/apm-cli   # or however APM is installed
apm install strands-spec-oracle
```

APM will deploy `.claude/CLAUDE.md` to your project so Claude Code picks it up
automatically.

---

## Architecture

```
spec_oracle/
├── agent.py           # Strands Agent + Bedrock + Rich CLI
├── chunker.py         # Splits .md files into heading-level chunks
├── decider_client.py  # HTTP client for Decider 2B /v1/systemone
└── handlers.py        # SpecContextInterventionHandler (before_model_call)

decisions/
└── spec_relevance_scoring.md   # ← Reusable decision pattern
```

### The decision

**Pattern:** Context & Memory  
**Decider question type:** `score` (0 = irrelevant, 2 = directly answers)  
**Threshold:** 0.55 normalised (configurable via `RELEVANCE_THRESHOLD`)

Each spec chunk is scored independently. Because the Decider server keeps the
model warm, chunking a 50-file corpus costs only the KV-cache overhead per
question — not a full model reload.

### Two wiring options

**Option A — InterventionHandler** (transparent): `SpecContextInterventionHandler`
hooks `before_model_call`, scores chunks, and injects only the relevant ones via
`Guide`. The agent loop never sees the filtering.

**Option B — Explicit tool**: `query_specs(question)` calls Decider 2B directly
and returns formatted context for the model to reason over.

Both are shown in the code. The `InterventionHandler` is the reusable pattern.

---

## Reusable decision pattern

See [`decisions/spec_relevance_scoring.md`](decisions/spec_relevance_scoring.md)
for the full reusable pattern — typed question, wiring code, configuration notes,
and accuracy guidance. Drop it into any Strands agent with a markdown knowledge base.

---

## Token savings (measured on demo corpus)

Demo corpus: **28 spec files · 313 chunks · ~24,840 tokens total**

Run `python benchmark.py --specs ./demo/specs` to reproduce these numbers.
All figures below are real measured output from `benchmark.py`.

> **Note:** The benchmark runs 10 queries × 313 chunks each. On CPU (Apple Silicon)
> each query takes ~40s, so the full benchmark run takes **~6 minutes** to complete.

| Query | Chunks used | Tokens used | Tokens saved | Saved % |
|-------|------------|-------------|-------------|---------|
| "retry strategy for failed payments" | 6 | ~802 | ~24,038 | 97% |
| "handle a card decline" | 6 | ~860 | ~23,980 | 97% |
| "payment status state machine" | 6 | ~787 | ~24,053 | 97% |
| "set up webhooks + verify signatures" | 6 | ~886 | ~23,954 | 96% |
| "rate limits for write endpoints" | 6 | ~366 | ~24,474 | 99% |
| "handle a customer dispute" | 6 | ~612 | ~24,228 | 98% |
| "set up Apple Pay" | 4 | ~480 | ~24,360 | 98% |
| "API key scopes for refunds" | 5 | ~337 | ~24,503 | 99% |
| "subscription dunning on failure" | 6 | ~751 | ~24,089 | 97% |
| "presentment vs settlement currency" | 1 | ~166 | ~24,674 | 99% |
| **Average** | **5.2** | **~604** | **~24,235** | **97.6%** |

Decider 2B latency: ~127ms/chunk · ~39s/query on CPU (Apple Silicon: ~50ms/chunk · ~16s/query)

---

## Demo Video

[![Spec Oracle Demo](https://img.youtube.com/vi/225LgExniVs/0.jpg)](https://youtu.be/225LgExniVs)

---

## License

Apache 2.0 — see [LICENSE](LICENSE).
