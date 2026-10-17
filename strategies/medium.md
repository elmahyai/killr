# Strategy: medium

One orchestrator owns this package's Python. It does not start a Rust agent. Python functions go out in batches that share an R file. One proof per function. This is not one agent per function. The batch returns to the orchestrator, as `strategies/orchestrator.md` says. The model is the first match in that file.

If Fortran or C that computes turns up, stop and follow the kernel switch in `strategies/orchestrator.md`.
