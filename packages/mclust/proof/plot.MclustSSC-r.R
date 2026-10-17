.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")
proof <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
source(file.path(proof, "plot_trace.R"))
X <- as.matrix(read.csv(file.path(proof, "MclustSSC_X.csv")))
cl <- read.csv(file.path(proof, "MclustSSC_class.csv"))[[1L]]
mod <- MclustSSC(X, cl, verbose = FALSE)
E <- new.env(parent = asNamespace("mclust"))
cases <- list(
  classification = function() mclust2Dplot(
    data = mod$data, what = "classification", classification = mod$classification,
    z = mod$z, parameters = mod$parameters, addEllipses = FALSE
  ),
  uncertainty = function() mclust2Dplot(
    data = mod$data, what = "uncertainty", classification = mod$classification,
    z = mod$z, parameters = mod$parameters, addEllipses = FALSE
  )
)
pdf(NULL)
out <- character(0)
for (nm in names(cases)) {
  trace_start()
  cases[[nm]]()
  trace_stop()
  out <- c(out, paste0("CASE ", nm), .LOG$out)
}
writeLines(out, file.path(proof, "../docs/output/plot.MclustSSC-r.txt"))
one <- cases$classification
one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[i] <- as.numeric(Sys.time()) - t0
}
writeLines(sprintf("%.17g", median(elapsed) * 1000),
           file.path(proof, "../docs/output/plot.MclustSSC-r-time.txt"))
dev.off()
