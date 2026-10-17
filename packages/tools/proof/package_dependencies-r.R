suppressPackageStartupMessages(library(tools))

one <- function() {
  db <- matrix(c(
    "a", "b, c", "d", NA, NA, NA,
    "b", NA, "a", NA, NA, NA,
    "c", NA, NA, NA, NA, NA
  ), nrow = 3, byrow = TRUE)
  colnames(db) <- c("Package", "Depends", "Imports", "LinkingTo", "Suggests", "Enhances")
  db2 <- matrix(c(
    "a", "b", NA, NA, NA, NA,
    "b", "c", NA, NA, NA, NA,
    "c", NA, NA, NA, NA, NA
  ), nrow = 3, byrow = TRUE)
  colnames(db2) <- colnames(db)
  fmt <- function(x) paste(paste(names(x), vapply(x, function(v) paste(v, collapse=","), ""), sep=":"), collapse=" ")
  paste0(
    fmt(package_dependencies(c("a", "b"), db = db)), "\n",
    fmt(package_dependencies("a", db = db, recursive = TRUE)), "\n",
    fmt(package_dependencies("a", db = db, reverse = TRUE)), "\n",
    fmt(package_dependencies("a", db = db2, recursive = TRUE)), "\n",
    fmt(package_dependencies("c", db = db2, reverse = TRUE, recursive = TRUE)), "\n"
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
