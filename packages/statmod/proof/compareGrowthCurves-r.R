suppressPackageStartupMessages(library(statmod))
if (as.character(packageVersion("statmod")) != "1.5.2") stop("expected statmod 1.5.2")

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- normalizePath(sub("^--file=", "", file_arg[[1]]))
root <- normalizePath(file.path(dirname(script), ".."))
out_dir <- file.path(root, "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

main_group <- function() {
  c("B", "B", "A", "A", "A", "C", "C", "D", NA)
}

main_y <- function() {
  matrix(
    c(
      1.0, 1.2, 1.1, 0.9,
      1.1, 1.3, 1.0, 1.0,
      2.0, 2.1, 1.9, 2.2,
      2.2, 2.0, 2.3, 2.1,
      2.1, NA, 2.0, 2.0,
      3.0, 3.2, 3.1, 2.9,
      3.1, 3.0, NA, 3.2,
      4.0, 4.1, 4.2, 4.0,
      0.5, 0.4, 0.6, 0.5
    ),
    nrow = 9,
    byrow = TRUE
  )
}

collect <- function(tab) {
  c(tab$Stat, tab$P.Value, tab$adj.P.Value)
}

one <- function() {
  set.seed(424242)
  main <- NULL
  capture.output(
    main <- compareGrowthCurves(main_group(), main_y(), nsim = 40, times = c(1, 3, 4), verbose = TRUE)
  )
  set.seed(7)
  numeric_groups <- compareGrowthCurves(
    c(10, 2, 10, 2, 2),
    matrix(
      c(
        5.0, 5.2, 5.1,
        1.0, 1.4, 1.2,
        5.3, 4.9, 5.0,
        1.3, 1.1, 1.5,
        0.9, 1.2, 1.0
      ),
      nrow = 5,
      byrow = TRUE
    ),
    nsim = 25,
    verbose = FALSE,
    adjust = "bonferroni",
    n0 = 1
  )
  set.seed(99)
  chosen <- compareGrowthCurves(
    main_group()[1:7],
    main_y()[1:7, ],
    levels = c("C", "A"),
    nsim = 15,
    verbose = FALSE,
    adjust = "BH"
  )
  c(collect(main), collect(numeric_groups), collect(chosen))
}

example <- capture.output({
  set.seed(424242)
  print(compareGrowthCurves(main_group(), main_y(), nsim = 40, times = c(1, 3, 4), verbose = TRUE))
})
writeLines(example, file.path(out_dir, "compareGrowthCurves-r.txt"))

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(sprintf("%.17g", as.numeric(value)), collapse = ","), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
