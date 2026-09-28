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
→ purpose/prediction checkpoint
→ synthetic experiment
→ validation
→ interpretation checkpoint
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

Open http://127.0.0.1:8000 and select **Run synthetic experiment**. No API key,
external service, or package installation is required.

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
Real LLM access, MCP/tool-protocol integration, larger benchmark coverage,
and production persistence are future extensions rather than current claims.
