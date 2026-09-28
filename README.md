# SocraticLoop MVP

SocraticLoop is an agentic research-assistant prototype for iterative machine
learning experiments. This first vertical slice runs without an LLM or API.
It uses deterministic role implementations with the same boundaries planned
for future Planner, Socratic Questioner, and Analyst LLM roles.

## What the demo shows

```text
Research question
→ literature retrieval
→ Planner experiment proposal
→ purpose/prediction checkpoint (pause for researcher)
→ synthetic experiment + validation
→ interpretation checkpoint (pause for researcher)
→ evidence-based research-state update
```

The scenario studies validation-loss instability after a learning-rate change.
The local literature corpus includes Leslie N. Smith's *Cyclical Learning
Rates for Training Neural Networks* ([source](https://arxiv.org/abs/1506.01186)).
The executor injects a planned/actual configuration mismatch so the Analyst
must mark the conclusion inconclusive rather than treat an unstable metric as
valid evidence for the hypothesis.

## Run locally

From the repository root:

```powershell
python -m unittest discover -s tests -v
python app.py
```

Open http://127.0.0.1:8000 and select **Run synthetic experiment**. The browser
UI is intentionally CLI-style: it shows a conversational transcript while the
Research State remains visible beside it. The API owns the session and pauses
at each checkpoint, so the user must answer before the next stage proceeds.
No API key, external service, or package installation is required.

The local server exposes the same flow as JSON endpoints:

- `POST /api/sessions`: start a deterministic research session.
- `GET /api/sessions/{session_id}`: read the current research state.
- `POST /api/sessions/{session_id}/checkpoints`: submit a checkpoint answer.
- `GET /api/demo`: run the complete flow in one response for regression/debugging.

Sessions are currently in-memory and intended for the local demo. A future
implementation can replace this store with persistent storage without changing
the conversational contract.

## Repository layout

- `socratic_loop/contracts.py`: research-state and checkpoint contracts.
- `socratic_loop/retrieval.py`: deterministic local literature retrieval.
- `socratic_loop/roles.py`: deterministic role provider boundary.
- `socratic_loop/experiment.py`: synthetic executor and validator.
- `socratic_loop/workflow.py`: end-to-end orchestrator.
- `data/`: benchmark scenario and literature records.
- `frontend/`: minimal user-facing demo.
- `tests/`: workflow regression tests.

The demo intentionally separates literature evidence from experiment evidence.
The product interaction is marked as a CLI-style conversational workflow; the
web page is its browser implementation, not a separate product concept. Real
LLM access, MCP/tool-protocol integration, larger benchmark coverage, and
production persistence are future extensions rather than current claims.
