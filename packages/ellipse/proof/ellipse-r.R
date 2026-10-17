suppressPackageStartupMessages(library(ellipse))
options(digits = 17)

dir.create("packages/ellipse/docs/output", recursive = TRUE, showWarnings = FALSE)
cases <- list(
  list(x = 0.35, scale = c(2, 1.5), centre = c(0.2, -0.4),
       level = 0.90, npoints = 17),
  list(x = matrix(c(4, 1.2, 1.2, 9), 2, 2), scale = NULL,
       center = c(-1.1, 2.3), level = 0.95, which = c(2, 1), npoints = 33),
  list(x = -0.8, scale = c(0.7, 2.1), centre = c(3, 0),
       t = 1.7, npoints = 64)
)

run_case <- function(z) {
  args <- z
  if (is.null(args$scale)) args$scale <- NULL
  args <- args[!vapply(args, is.null, logical(1))]
  do.call(ellipse, args)
}

invisible(run_case(cases[[1]]))
elapsed <- numeric(20)
result <- vector("list", length(cases))
for (i in seq_len(20)) {
  t0 <- Sys.time()
  for (j in seq_along(cases)) result[[j]] <- run_case(cases[[j]])
  elapsed[i] <- as.numeric(difftime(Sys.time(), t0, units = "secs"))
}
for (j in seq_along(result)) {
  write.table(result[[j]],
              file = sprintf("packages/ellipse/docs/output/ellipse-r-case%d.txt", j),
              row.names = FALSE, col.names = FALSE, quote = FALSE,
              sep = " ")
}
cat(sprintf("r_ms %.17g\n", median(elapsed) * 1000))
