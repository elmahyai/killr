# Label placer zero index

R indexes from 1. In `label_placer_middle()`, the neighbours of the middle point are `x[m - 1]`, `x[m]`, and `x[m + 1]`. When `m` is 1 (a section of 2 or 3 points), `x[0]` is `numeric(0)`, so R silently drops that neighbour and keeps 2 points. A section of 1 point makes `x[0]` empty and `x[-1]` drop an element, so R's result is undefined there.

The Python port keeps the neighbours that exist and raises `ValueError` for a section with fewer than 2 points. `label_placer_simple()` takes R's 1-based `index` values and echoes them unchanged, so the output matches R. Convert to 0-based only when reading the arrays.
