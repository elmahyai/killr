kuantile with many probs was wrong. It sorted the concatenated (lower, upper) order-statistic pairs and then reshaped to (m, 2), so the pairs were scrambled when neighbouring probs shared a rank. Fixed in orderstats.kuantile by keeping each prob's pair in its own row, with no sort.

The R reference for type 7 is base R quantile(x, probs, type = 7), not quantreg's kuantile. R's own kuantile has the same sort-then-reshape bug, and on 1:99/100 it differs from quantile() by about 0.07 for sin(1:92) * 10 + (1:92) / 7. NumPy quantile(method="linear") matches base R within about 1e-14.
