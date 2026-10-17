suppressPackageStartupMessages(library(tools))

one <- function() {
  acc <- function(text) list(structure(paste0("\\", "'"), latex_tag = "MACRO"), structure(text, latex_tag = "TEXT"))
  block <- list(structure(paste0("\\", "'"), latex_tag = "MACRO"), structure(list(structure("e", latex_tag = "TEXT")), latex_tag = "BLOCK"))
  aa <- list(structure(paste0("\\", "aa"), latex_tag = "MACRO"))
  paste0(
    deparseLatex(latexToUtf8(acc("e"))), "\n",
    deparseLatex(latexToUtf8(acc(" e"))), "\n",
    deparseLatex(latexToUtf8(aa)), "\n",
    deparseLatex(latexToUtf8(block)), "\n"
  )
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
