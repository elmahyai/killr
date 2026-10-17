suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
out_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/docs/output"
source(file.path(proof_dir, "plot_trace.R"))
source(file.path(proof_dir, "plot_record.R"))  # make_fixtures

fx <- make_fixtures()
X3 <- fx$data3
X2 <- fx$data2
dimnames(X3) <- NULL
dimnames(X2) <- NULL

cases <- list(
  vvv_loglik = list(X = X3, model = "VVV", what = "loglik"),
  vvv_merge = list(X = X3, model = "VVV", what = "merge"),
  eii_loglik = list(X = X2, model = "EII", what = "loglik")
)

write_matrix <- function(m, path) {
  lines <- apply(m, 1, function(r) paste(sprintf("%.17g", r), collapse = "\t"))
  writeLines(lines, path)
}

# The hc objects are built here and their values are written for the Python
# translation: the two-row merge matrix, the initial partition, and the data.
hc_objects <- list()
for (nm in names(cases)) {
  cs <- cases[[nm]]
  h <- hc(cs$X, modelName = cs$model)
  hc_objects[[nm]] <- h
  write_matrix(matrix(as.numeric(h), nrow = 2), file.path(proof_dir, paste0("plot.hc_", nm, "_pairs.txt")))
  writeLines(sprintf("%d", as.integer(attr(h, "initialPartition"))), file.path(proof_dir, paste0("plot.hc_", nm, "_init.txt")))
  write_matrix(cs$X, file.path(proof_dir, paste0("plot.hc_", nm, "_data.txt")))
  writeLines(c(cs$model, cs$what), file.path(proof_dir, paste0("plot.hc_", nm, "_args.txt")))
}

out <- character(0)
pdf(NULL)
for (nm in names(cases)) {
  h <- hc_objects[[nm]]
  cs <- cases[[nm]]
  .LOG$out <- character(0)
  trace_start()
  trace("axis",
        tracer = quote(if (!is.null(at)) .add("V", paste0("axis", side), .fmtn(at))),
        where = asNamespace("graphics"), print = FALSE)
  res <- plot(h, what = cs$what)
  trace_stop()
  untrace("axis", where = asNamespace("graphics"))
  .value("usr", par("usr"))
  .value("merge", res$merge)
  .value("height", res$height)
  .value("order", res$order)
  out <- c(out, paste0("CASE\t", nm), .LOG$out)
}
dev.off()
writeLines(out, file.path(out_dir, "plot.hc-r.txt"))

# Timing: the data computation that plot.hc does before it draws. That is
# as.hclust (with the classification log-likelihood for "loglik") and the
# dendrogram structure from as.dendrogram. The drawing is not timed.
timed_case <- cases[["vvv_loglik"]]
h_timed <- hc_objects[["vvv_loglik"]]
one <- function() as.dendrogram(as.hclust(h_timed, what = "loglik"), hang = 0)
invisible(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  invisible(one())
  elapsed[i] <- as.numeric(Sys.time()) - t0
}
writeLines(sprintf("%.17g", median(elapsed) * 1000), file.path(out_dir, "plot.hc-r-time.txt"))
cat("ok\n")
