`x**1.5D0` is `pow`, not `x * sqrt(x)`; they differ by about 4e-16. An integer power is a multiplication. Squaring the NEWUOA residual with `pow` is what the recorded point count expects.
