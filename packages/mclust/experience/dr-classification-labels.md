# DR classification labels

For an `Mclust` fit, the translated `mclust_dr` result holds `classification` as one integer label per observation, the factor codes of `as.factor(object$classification)`, as R does. `mixcomp` is the per-observation mixture component, and `class2mixcomp` maps each component to its class.

`predict.MclustDR` takes `nclass` and the class labels from the distinct values of `classification`. `summary.MclustDR` takes `n` as `table(classification)`.

For an `MclustDA` fit, `classification` still holds only the class level names. Mapping `mixcomp` through `class2mixcomp` is the way to get the per-observation label there.
