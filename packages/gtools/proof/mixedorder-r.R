.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(gtools))
stopifnot(as.character(packageVersion("gtools")) == "3.9.5")

flat <- function(x) {
  if (is.null(x)) return(numeric(0))
  as.numeric(x)
}

one <- function() {
  x <- rev(c(
    "AA 0.50 ml", "AA 1.5 ml", "AA 500 ml", "AA 1500 ml",
    "EXP 1", "AA 1e3 ml", "A A A", "1 2 3 A", "NA", NA, "1e2",
    "", "-", "1A", "1 A", "100", "100A", "Inf"
  ))
  chapters <- c(
    "V. Non Sequiturs", "II. More Nonsense", "I. Nonsense",
    "IV. Nonesensical Citations", "III. Utter Nonsense"
  )
  vals <- c("3E1", "2E3", "4e0")
  c(
    flat(mixedorder(x)),
    flat(mixedorder(x, decreasing = TRUE)),
    flat(mixedorder(x, na.last = FALSE)),
    flat(mixedorder(x, blank.last = TRUE)),
    flat(mixedorder(c(3, 1, 2))),
    flat(mixedorder(chapters, numeric.type = "roman")),
    flat(mixedorder(vals)),
    flat(mixedorder(vals, scientific = FALSE))
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":[%s],"median_ms":%.17g}\n', paste(value, collapse = ","), median(elapsed) * 1000))
