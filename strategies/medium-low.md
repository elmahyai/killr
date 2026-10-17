# Strategy: medium-low

One orchestrator owns the package. It does not translate a kernel itself.

- One Rust sub-agent gets one crate: the Fortran and numerical C for that kernel. It does not translate the R wrappers.
- Python functions go out in batches that share an R file. One proof per function. The batch returns to the orchestrator, as `strategies/orchestrator.md` says. The model for the Python batch and for the Rust sub-agent is the first match in that file.
