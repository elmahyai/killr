# Strategy: small

One agent translates the remaining functions. It does not start child agents. It writes one proof per function. It returns the proof result, the waiting names, and the one experience path, as `strategies/orchestrator.md` says. The orchestrator records the check. The model is the first match in that file.

If Fortran or C that computes turns up, stop and follow the kernel switch in `strategies/orchestrator.md`.
