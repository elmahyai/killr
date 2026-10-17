# Formula operator order

When splitting a formula into `(piece, operator)` pairs, the operator belongs
to the piece before it; the final piece has no following operator. Expansion
loops must therefore read the preceding tuple's operator, or `*` will silently
lose the right-hand main effect.
