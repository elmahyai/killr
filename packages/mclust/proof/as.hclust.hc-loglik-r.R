.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(mclust))
if (packageDescription("mclust")$Version != "6.1.3") stop("expected mclust 6.1.3")

proof_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/proof"
out_dir <- "/home/ahmed/killr_projects/killr/packages/mclust/docs/output"

# Same fixed data as plot_record.R make_fixtures(): 60 points, 3 columns.
i <- 1:60
g3 <- (i - 1) %% 3
x1 <- 1.3 * cos(0.37 * i) + 2.5 * g3
x2 <- 0.9 * sin(0.53 * i) + 0.8 * g3 - 0.5
x3 <- 0.4 * cos(0.9 * i) + 0.2 * sin(1.7 * i)
X3 <- cbind(x1, x2, x3)
dimnames(X3) <- NULL
X2 <- X3[, 1:2, drop = FALSE]

datasets <- list(
  vvv = list(X = X3, model = "VVV"),
  eii = list(X = X2, model = "EII")
)
hc_objects <- list()
write_matrix <- function(m, path) {
  lines <- apply(m, 1, function(r) paste(sprintf("%.17g", r), collapse = "\t"))
  writeLines(lines, path)
}
for (nm in names(datasets)) {
  ds <- datasets[[nm]]
  h <- hc(ds$X, modelName = ds$model)
  hc_objects[[nm]] <- h
  write_matrix(matrix(as.numeric(h), nrow = 2), file.path(proof_dir, paste0("as.hclust.hc-loglik_", nm, "_pairs.txt")))
  writeLines(sprintf("%d", as.integer(attr(h, "initialPartition"))), file.path(proof_dir, paste0("as.hclust.hc-loglik_", nm, "_init.txt")))
  write_matrix(ds$X, file.path(proof_dir, paste0("as.hclust.hc-loglik_", nm, "_data.txt")))
  writeLines(c(ds$model, "loglik"), file.path(proof_dir, paste0("as.hclust.hc-loglik_", nm, "_args.txt")))
}

# Trimming cases with a fixed cloglik vector. ldend takes its cloglik from
# cloglik.hc, so these replace cloglik.hc in the mclust namespace for one call.
# The vectors are written to files so the Python side reads the same numbers.
fixed <- list(
  neg_early = c(-50, -30, -35, -20, -25, -10, -5, 0, rep(NA, 52)),
  neg_late = c(-100, -90, -80, -70, -60, -55, -50, -52, -40, -30, -20, -10, rep(NA, 48)),
  monotone = seq(-100, 50, length.out = 60)
)
for (nm in names(fixed)) {
  writeLines(sprintf("%.17g", fixed[[nm]]), file.path(proof_dir, paste0("as.hclust.hc-loglik_fixed_", nm, "_cloglik.txt")))
}

# name, dataset, maxG, fixed cloglik name (NULL = cloglik.hc computes it)
cases <- list(
  list(name = "vvv_loglik", ds = "vvv", maxG = NULL, fixed = NULL),
  list(name = "eii_loglik", ds = "eii", maxG = NULL, fixed = NULL),
  list(name = "vvv_loglik_maxG5", ds = "vvv", maxG = 5, fixed = NULL),
  list(name = "eii_loglik_maxG3", ds = "eii", maxG = 3, fixed = NULL),
  list(name = "vvv_fixed_neg_early", ds = "vvv", maxG = NULL, fixed = "neg_early"),
  list(name = "vvv_fixed_neg_early_maxG2", ds = "vvv", maxG = 2, fixed = "neg_early"),
  list(name = "vvv_fixed_neg_late", ds = "vvv", maxG = NULL, fixed = "neg_late"),
  list(name = "vvv_fixed_neg_late_maxG4", ds = "vvv", maxG = 4, fixed = "neg_late"),
  list(name = "vvv_fixed_monotone", ds = "vvv", maxG = NULL, fixed = "monotone"),
  list(name = "vvv_fixed_monotone_maxG20", ds = "vvv", maxG = 20, fixed = "monotone")
)

run_loglik <- function(h, maxG, fixed_name) {
  if (is.null(fixed_name)) {
    return(as.hclust(h, what = "loglik", maxG = maxG))
  }
  cll <- fixed[[fixed_name]]
  orig <- get("cloglik.hc", envir = asNamespace("mclust"))
  assignInNamespace("cloglik.hc", function(hcObj, maxG = NULL) cll, "mclust")
  on.exit(assignInNamespace("cloglik.hc", orig, "mclust"))
  as.hclust(h, what = "loglik", maxG = maxG)
}

fmt <- function(v) {
  v <- as.double(v)
  ifelse(is.na(v), "NA", sprintf("%.17g", v))
}

out <- character(0)
timing <- character(0)
for (cs in cases) {
  h <- hc_objects[[cs$ds]]
  res <- run_loglik(h, cs$maxG, cs$fixed)
  cloglik <- as.vector(attr(res, "cloglik"))
  out <- c(out,
           paste0("CASE\t", cs$name),
           paste0("merge\t", paste(fmt(as.vector(res$merge)), collapse = " ")),
           paste0("height\t", paste(fmt(res$height), collapse = " ")),
           paste0("order\t", paste(fmt(res$order), collapse = " ")),
           paste0("cloglik\t", paste(fmt(cloglik), collapse = " ")))

  # Timing: one untimed call, then the median of 20 timed calls.
  # R time is the whole as.hclust(loglik) call, which includes cloglik.hc
  # unless the case has a fixed cloglik.
  invisible(run_loglik(h, cs$maxG, cs$fixed))
  elapsed <- numeric(20)
  for (k in seq_len(20)) {
    t0 <- as.numeric(Sys.time())
    invisible(run_loglik(h, cs$maxG, cs$fixed))
    elapsed[k] <- as.numeric(Sys.time()) - t0
  }
  timing <- c(timing, sprintf("%s\t%.17g", cs$name, median(elapsed) * 1000))
}

writeLines(out, file.path(out_dir, "as.hclust.hc-loglik-r.txt"))
writeLines(timing, file.path(out_dir, "as.hclust.hc-loglik-r-time.txt"))
cat("ok\n")
