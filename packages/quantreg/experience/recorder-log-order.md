# Recorder log order

When an R plot proof wraps a drawing call in a log recorder, the log line must be built before the log vector is read. R evaluates `c(E$log, paste(...))` left to right, and a value argument such as `E$value("ret", E$plot.rqs(fit))` can draw and append to `E$log` while the arguments are forced. If the old `E$log` is read first, the nested panel records are overwritten and only the last value survives.

Fix: in `put()`, build the line with `rec_fields(...)` in its own statement, then assign `E$log <- c(E$log, line)`. See `packages/quantreg/proof/plot_record.R`.

A symptom is a log with only `V` lines and no `T`, `W`, or `P` lines, while a direct call to the same recorder logs them.
