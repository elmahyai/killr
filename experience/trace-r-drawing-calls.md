# Trace R drawing calls in proofs

To compare what an R chart function draws, call `trace()` inside the package that calls the drawing function. A package reaches `rect`, `matplot`, or `text` through its own imports, so use `where = asNamespace("<pkg>")`. A tracer on `graphics` alone misses those calls. For `plot.default` and `lines.default` called from the package, `where = asNamespace("graphics")` works.

Trace the `.default` method for a generic. Tracing `text` fails with "object 'y' not found" because the generic has no `y` argument. Trace `text.default` instead.

Wrap `trace()` and `untrace()` in `capture.output()` so their messages stay out of the proof output. Trace only the untimed call. Time a copy of the data lines with no drawing.
