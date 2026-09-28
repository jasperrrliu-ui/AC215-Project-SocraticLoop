# Working conventions

Read `README.md` and `AGENT_PROGRESS.md` before changes. Keep benchmark
scenario preparation, workflow orchestration, role providers, retrieval,
experiment execution, validation, and presentation in separate modules.

Deterministic demo behavior must be labeled as mock or synthetic. Keep
literature evidence separate from experiment evidence. Do not put secrets or
real private research records in the repository. Run relevant tests after
changes and update `AGENT_PROGRESS.md` with actual checks, decisions,
blockers, and next steps before stopping.
