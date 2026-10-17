suppressPackageStartupMessages(library(tools))

PKG <- "/home/ahmed/killr_projects/killr/packages/tools/proof/checkTnF_pkg"

one <- function() {
  res <- checkTnF(dir = PKG)
  lines <- character()
  for (path in names(res)) {
    lines <- c(lines, path)
    for (i in seq_along(res[[path]])) {
      lines <- c(lines, paste(deparse(res[[path]][[i]], width.cutoff = 500), collapse = ""))
    }
  }
  paste0(paste(lines, collapse = "\n"), "\n")
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
