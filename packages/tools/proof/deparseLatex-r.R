suppressPackageStartupMessages(library(tools))

one <- function() {
  x <- list(
    structure("\\emph", latex_tag = "MACRO"),
    structure(list(structure("x", latex_tag = "TEXT")), latex_tag = "BLOCK"),
    structure(list(structure("y", latex_tag = "TEXT")), latex_tag = "MATH")
  )
  paste0(deparseLatex(x), "\n", deparseLatex(x, dropBraces = TRUE), "\n")
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(value, sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
