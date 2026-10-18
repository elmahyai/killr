# Scoped state restoration

For `conflicted`, keep package exports, attached-package order, and declared
preferences in an explicit process-local registry. Do not install shims into
Python's import machinery; callers provide the registry when scouting conflicts.

When translating R `withr` helpers that mutate interpreter state, expose a
small explicit process-local state object in Python and make both `with_*`
and `local_*` restore in `finally`.  Python has no R search path or `.libPaths`
global, so proofs should compare the translated state API before, during, and
after the scope rather than relying on unrelated Python import state.
