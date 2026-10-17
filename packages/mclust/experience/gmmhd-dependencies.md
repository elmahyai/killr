GMMHD dependency boundary

`gmmhd` fits through `mclustBIC` and uses `MclustDA` for classification; both are translated now (`MclustDA` for the EDDA model type only, `mclustBIC` for one component), so the remaining waits are `Mclust` (`me`) and the R package `geometry`, and cluster-core extraction and summary/printing are independent.
