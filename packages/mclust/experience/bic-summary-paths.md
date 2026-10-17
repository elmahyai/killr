# BIC summary paths

`summaryMclustBIC` and `summaryMclustBICn` preserve the selected BIC entry
and attach the fitted one-component normal result; the noise variant uses
`G = 0` and `Vinv` for its null model.

With `G = 1`, `summaryMclustBIC` takes the one-component branch: `mvn` on the best model, `z` all ones, and `bic` from the top entry of the BIC matrix. The BIC penalty must use the requested model name (`XXX`/`EEE`/`VVV` carry 5 parameters, `XII`/`EII`/`VII` carry 3). Using a fixed name gave the wrong model choice in 2-D.

With `G > 1`, the best model is refitted from `hclass(hcPairs, G)` (or `qclass` in one dimension) through `me`, and one extra `mstep` runs when the mixing proportions differ from the column means of `z`. Its `bic` is one value recomputed from that fit, not the top-3 vector. `Mclust` takes the first entry of `bic`: the top BIC for `G = 1`, and the single value for `G > 1`. `hclass` reads the hierarchical start's `initialPartition`, so the `hc` result must carry it as an attribute.

The `hc` default partition is `1:n`, so `dupPartition` (the kmeans path for duplicate rows) is not reached by `mclustBIC` or `Mclust`. The partition is renumbered by first appearance (R `partconv`, consecutive), not in sorted order; sorted labels change the merge ids that `hc` returns, and the attribute must hold the renumbered vector.
