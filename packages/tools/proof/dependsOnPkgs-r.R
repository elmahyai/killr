suppressPackageStartupMessages(library(tools))

one <- function() {
  m <- matrix(c(
    "a", "b, R (>= 4.0)", NA, NA, "c", NA,
    "b", NA, "c", NA, NA, NA,
    "c", NA, NA, NA, NA, NA,
    "d", "a", NA, NA, NA, NA
  ), nrow = 4, byrow = TRUE)
  colnames(m) <- c("Package", "Depends", "Imports", "LinkingTo", "Suggests", "Enhances")
  paste0(
    paste(dependsOnPkgs("c", installed = m), collapse = ","), "\n",
    paste(dependsOnPkgs("c", dependencies = "most", installed = m), collapse = ","), "\n",
    paste(dependsOnPkgs("c", dependencies = "all", recursive = FALSE, installed = m), collapse = ","), "\n",
    paste(dependsOnPkgs("b", recursive = FALSE, installed = m), collapse = ","), "\n"
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
