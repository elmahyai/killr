suppressPackageStartupMessages(library(fontawesome))

output <- file.path(
  "/home/ahmed/killr_projects/killr/packages/fontawesome/docs/output",
  "fa_png-r.png"
)
dir.create(dirname(output), recursive = TRUE, showWarnings = FALSE)

if (!requireNamespace("rsvg", quietly = TRUE)) {
  stop("fa_png proof blocked: the required R package rsvg is unavailable")
}

invisible(fa_png("r-project", file = output, fill = "red"))
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- Sys.time()
  invisible(fa_png("r-project", file = output, fill = "red"))
  elapsed[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
}
cat(sprintf("r_ms %.17g\n", median(elapsed) * 1000))
