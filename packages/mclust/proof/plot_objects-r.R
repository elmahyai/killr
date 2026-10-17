# Fits the objects the mclust plot proofs draw, and dumps each one to JSON.
# The fits are R's own. The plot proofs read the dumped files, not these fits.
.libPaths(c(path.expand("~/R/x86_64-pc-linux-gnu-library/4.5"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
here <- dirname(sub("^--file=", "", grep("^--file=", commandArgs(FALSE), value = TRUE)))
source(file.path(here, "plot_record.R"))
source(file.path(here, "plot_object_io.R"))
fx <- make_fixtures()

X2 <- fx$data2
colnames(X2) <- c("x1", "x2")
X1 <- matrix(X2[, 1], ncol = 1, dimnames = list(NULL, "x1"))

m2 <- Mclust(X2, G = 3, verbose = FALSE)
X3 <- fx$data3
colnames(X3) <- c("x1", "x2", "x3")
m3 <- Mclust(X3, G = 3, verbose = FALSE)
m1 <- Mclust(X1, G = 2, verbose = FALSE)
d1 <- densityMclust(X1[, 1], G = 2, plot = FALSE, verbose = FALSE)
d2 <- densityMclust(X2, G = 2, plot = FALSE, verbose = FALSE)

dump_mclust_object(m2, file.path(here, "plot_object_mclust2d.json"))
dump_mclust_object(m1, file.path(here, "plot_object_mclust1d.json"))
dump_mclust_object(m3, file.path(here, "plot_object_mclust3d.json"))
dump_mclust_object(d1, file.path(here, "plot_object_density1d.json"))
dump_mclust_object(d2, file.path(here, "plot_object_density2d.json"))
cat("classes", class(m2), class(m1), class(d1), class(d2), "\n")
cat("G", m2$G, m1$G, d1$G, d2$G, "d", m2$d, m1$d, d1$d, d2$d, "\n")
