.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
if (packageDescription("mix")$Version != "1.0-13") stop("expected mix 1.0-13")

# Writes the stlouis data set of mix 1.0-13 for the Python proofs. Missing values are
# written as NaN, the 69 x 7 matrix as is, with the column names of the data set.
data("stlouis", package = "mix", envir = environment())
x <- stlouis
write.csv(x, file = "stlouis.csv", row.names = FALSE, na = "NaN")
