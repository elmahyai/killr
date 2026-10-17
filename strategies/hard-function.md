# Strategy: hard-function

This path is only when the user names it. It is not stored on the package.

One agent translates one function. It reads that function's source and help. It does not read the rest of the package and it does not start further agents. The model is the first match in `strategies/orchestrator.md`: one `claude-haiku-5-5-thinking-high` retry, then stop and report.

Use it for one function whose proof failed and needs a fresh attempt. Do not use it as the default for a package. Do not restart a miss that is already recorded: `royston`, `ca.po`, `ode.1D`, `MclustDRsubsel`, `MclustDRsubsel_cluster`, and `MclustDRsubsel1cycle`.
