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

## Feasibility-study benchmark

The feasibility benchmark is separate from the deterministic product demo. It
uses eight versioned learning-rate research records across four fault families:
valid evidence, configuration mismatch, numerical failure, and metric-contract
mismatch. Every case has a hidden oracle. Prompts never contain the oracle.

The four conditions isolate different mechanisms:

- `raw_record`: experiment record only; the small-model baseline.
- `validator_augmented`: raw record plus deterministic validator events.
- `socratic_checkpoint`: validator events plus a researcher purpose/prediction
  checkpoint.
- `gated_harness`: checkpoint condition plus a deterministic integrity policy:
  a fatal validation event forces `evidence_status=invalid` and
  `hypothesis_status=unresolved`. This is a safety guarantee, not improved LLM
  reasoning.

Providers must return this strict schema:

```json
{
  "detected_faults": ["numerical_failure"],
  "evidence_status": "invalid",
  "hypothesis_status": "unresolved",
  "next_action_code": "rerun_with_lower_learning_rate",
  "rationale": "One sentence."
}
```

The scorer reports schema compliance, fault precision/recall, evidence and
hypothesis correctness, exact next-action correctness, and unsafe hypothesis
updates. It scores the raw provider decision separately from the final gated
decision.

Export provider-neutral, blinded prompts:

```powershell
python scripts/run_feasibility.py --condition raw_record --write-prompts outputs/raw_prompts.jsonl
python scripts/run_feasibility.py --condition gated_harness --write-prompts outputs/gated_prompts.jsonl
```

An open model or coding-agent adapter can write one JSON object per line with
`scenario_id` plus the schema above, then be scored without oracle exposure:

```powershell
python scripts/run_feasibility.py --condition validator_augmented --responses outputs/qwen_responses.jsonl --provider-name qwen2.5-3b
```

An optional OpenAI Responses API adapter is implemented but never invoked by
default. It reads `OPENAI_API_KEY` only when explicitly selected and requires
the optional SDK (`pip install openai`):

```powershell
python scripts/run_feasibility.py --condition raw_record --provider openai --model YOUR_MODEL_ID
```

For the complete study, open `notebooks/feasibility_study_colab.ipynb` in
Colab, add a Colab Secret named `OPENAI_API_KEY`, and run all cells. The
notebook clones the repository, installs the optional SDK, runs the repository
tests, evaluates all four conditions, and prints the generated reports. The
same workflow can be run locally with:

```powershell
python scripts/run_all_conditions.py --provider openai --model YOUR_MODEL_ID
```

This benchmark is an evaluation contract, not a claim that the harness is
better or cheaper. It does not train or post-train a model. A coding-agent
comparison on the same prompt contract measures research-decision quality; a
future end-to-end coding-agent benchmark must separately provide an executable
ML repository and tool environment.
