# Agent progress

## Current status

Updated: 2026-09-28.

**In progress:** Corrected the feasibility-study target after the earlier
GPT-4.1-mini run measured only component ablations. Added the primary A-D
system contract: Codex/gpt-5.6-sol reference, Qwen2.5-Coder-3B raw, the same
Qwen model with SocraticLoop, and a future QLoRA adapter with SocraticLoop.
Added eight isolated executable tasks using deterministic, dependency-free
logistic-regression training. The two valid cases produce opposite conclusions
from real loss curves; configuration, numerical, and metric-contract faults
are explicit controlled injections. Hidden oracles are not copied into task
workspaces.

**Current checks:** `python -m unittest discover -s tests -v` passes 16 tests;
all eight executable tasks run locally; the supporting case yields validation
losses 0.182919, 0.10784, 0.149402 for learning rates 0.001, 0.01, 0.1, while
the refuting case makes 0.1 the best rate. Python compilation and
`git diff --check` pass.

**Current blocker:** The Codex reference runner is implemented, but the Codex
CLI cannot initialize its state database from the current restricted shell
(`state_5.sqlite` is read-only). No Codex baseline task completed or consumed a
result. Run the documented command from normal PowerShell. Qwen B/C are ready
for the new `notebooks/agent_benchmark_colab.ipynb`; they have not yet been run.
The QLoRA condition remains intentionally unclaimed until a disjoint training
set and adapter exist. A deterministic builder now creates 40 train and 8
validation records with train-only IDs, and a one-epoch QLoRA script/notebook
is implemented. The first T4 attempt reached training but failed at gradient
unscaling because BF16 gradients are unsupported on that AMP path. The trainer
now uses the standard k-bit preparation step, FP16 quantized forward compute,
FP32 trainable LoRA parameters, and explicitly disables BF16. The adapter has
not yet completed training or evaluation after this correction.

**Completed:** Read the AMDEX agent workflow materials (`AGENTS.md`, `README.md`,
`PRD.md`, and `AGENT_PROGRESS.md`) before continuing SocraticLoop MVP work.
Created the first deterministic vertical slice with explicit contracts,
local literature retrieval, role boundaries, a synthetic executor, validation,
research-state updates, a static frontend, and a regression test.

**Completed:** Replaced the initial three-case feasibility scaffold with a
versioned eight-case benchmark and four explicit ablation conditions:
`raw_record`, `validator_augmented`, `socratic_checkpoint`, and
`gated_harness`. The gate is measured separately as deterministic policy, not
as LLM reasoning.

**Implementation status:** The repository contains the uncommitted MVP files
documented in `README.md`. The demo runs locally at `http://127.0.0.1:8000`
and the static Site is published at
`https://socratic-loop-mvp.jliu-seeu.chatgpt.site`. Both versions do not
require an LLM/API.

**Decisions:** Keep the project subject as an agentic research assistant. Use
role interfaces for Planner, Socratic Questioner, and Analyst; implement
deterministic mock roles first; keep experiment execution and validation
deterministic; keep literature evidence separate from experiment evidence; and
leave real LLM access and MCP/tool-protocol integration as replaceable future
adapters. The product interaction is now marked as a CLI-style conversational
web frontend: the browser renders the terminal-like conversation, while the
API owns session state, checkpoint pause/resume, execution, validation, and
research-state updates.

**Next steps:** Export and run the frozen versioned prompts for Qwen under all
four conditions, then inspect the provider and final-gated reports separately.
Only after this benchmark audit should a same-contract OpenAI/coding-agent
reference be run. The OpenAI Responses API adapter is implemented but not
called; no API key is stored. Post-training and MCP/tool-protocol adapters
remain future work. The user will create the next commit/push, suggested
message: `Add feasibility study scaffold`.

The local API-backed conversational demo is now implemented. The published
static Site remains the earlier snapshot until this workflow is intentionally
republished.

## History

### 2026-09-27 — AMDEX workflow review and SocraticLoop handoff

Read the AMDEX repository instructions, README, PRD, and progress log. Learned
that the workflow requires requirements-first inspection, explicit boundaries
between domain packages and evaluation workflow, a shared model-gateway
boundary, clearly labeled deterministic mocks, independent provenance for
fixtures and runtime challenges, and durable progress logging. No SocraticLoop
application files were changed during this review. The initial MVP code patch
was rejected before application files were written because of an invalid patch
hunk; this remains an implementation blocker to resolve next.

### 2026-09-27 — Deterministic learning-rate MVP

Added `AGENTS.md`, `README.md`, typed research-state contracts, a deterministic
literature retriever, role provider, synthetic executor, validator, workflow
orchestrator, local JSON scenario/corpus, static frontend, and one workflow
regression test. The literature corpus includes Smith's learning-rate range
test paper and a clearly labeled synthetic capacity note. The executor injects
a planned/actual learning-rate mismatch and the analyst marks the result
inconclusive rather than treating the unstable metric as valid support.

Validation performed: `python -m unittest discover -s tests -v` passed (1 test);
`python -m compileall -q socratic_loop app.py` passed; `git diff --check`
passed; `GET /api/demo` returned HTTP 200 with retrieval, two checkpoints,
validation warnings, and an inconclusive interpretation; the browser UI was
opened and the demo button was run successfully. No LLM/API or MCP integration
was used.

### 2026-09-28 — Static Site migration

Added a static Site entrypoint under `site/index.html` and Sites metadata under
`.openai/hosting.json`. Because the local clone's Git index remained
write-protected, copied the exact static source into a writable Sites staging
repository, pushed commit `a60d139e7731042fb886aeba972b101fecf24b06`, saved
version 1, deployed it, and changed the Site audience to public. Browser
verification confirmed the public page shows the literature context, Planner,
human checkpoints, validation warnings, evidence, and inconclusive conclusion.

### 2026-09-28 — Commit/push attempt

The target clone's `.git/index.lock` remained inaccessible after a scoped write
permission request, so a writable alternate Git metadata directory was used to
create complete commit `9c10122d32188e972b05e5d8f7c000333970dfec`. Pushing that
commit to the GitHub `origin` failed because the shell has no GitHub HTTPS
credential; no password or token was requested or stored. The source files are
unchanged, and the commit remains available in the local staging metadata for
later push through an authenticated Git client.

### 2026-09-28 — CLI-style conversational demo

Marked the product interaction as a CLI-style conversational workflow and
implemented its browser version as an API-backed demo. `POST /api/sessions`
starts a session, the API pauses at the purpose/prediction checkpoint, then
continues through deterministic execution and validation after the user
answers. A second interpretation checkpoint is required before the Analyst
updates the research state. The frontend shows the terminal-like transcript
and the live research-state panel side by side.

Validation performed: the two workflow unit tests passed; Python compilation
passed; a live API session was started and completed through both checkpoint
requests; and the refreshed local browser page showed the new conversational
UI. No LLM/API key or MCP integration was added.

### 2026-09-28 — Feasibility-study scaffold

Added the original feasibility scaffold. It was later superseded because the
first Colab probe duplicated scenarios and scoring outside this versioned
contract.

Validation performed: six unit tests passed; direct and harness prompt export
each wrote three blinded prompts; `git diff --check` passed.

### 2026-09-28 — First GPU small-model feasibility probe

Used a user-approved Google Colab T4 runtime (Tesla T4, 14.6 GB VRAM), not a
GCP project resource. Installed BitsAndBytes 0.50.2 and ran
`Qwen/Qwen2.5-3B-Instruct` in 4-bit quantization. The model completed all
three direct and all three harness-condition prompts. The hidden oracle was
not included in model input.

The numerical comparison from that notebook is invalidated: it used manually
duplicated scenario values and a keyword-based scorer instead of the repository
contract. It remains evidence only that the 3B model can run in 4-bit on a T4
and that it can violate a strict enum schema. It does not establish a harness
effect. No post-training was performed.

### 2026-09-28 — Reproducible feasibility-benchmark redesign

Replaced the scaffold with eight versioned cases spanning valid evidence,
configuration mismatch, numerical failure, and metric-contract mismatch. Each
case has an explicit validity policy, required faults, exact action code, and
hidden oracle. Implemented four ablation conditions, strict schema validation,
fault precision/recall, unsafe-hypothesis-update measurement, and separate
provider versus final-gated decisions. Added an optional OpenAI Responses API
adapter that reads `OPENAI_API_KEY` only on explicit invocation, while external
open models and coding-agent adapters use the same JSONL prompt/response
contract. No API request was made.
