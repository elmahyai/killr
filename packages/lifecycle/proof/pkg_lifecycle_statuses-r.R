suppressPackageStartupMessages(library(lifecycle))
one <- function() {
  show <- function(df) {
    if (!nrow(df)) "EMPTY" else paste(df$fun, df$lifecycle, sep = "=", collapse = ",")
  }
  paste(
    show(pkg_lifecycle_statuses("lifecycle")),
    show(pkg_lifecycle_statuses("lifecycle", which = c("deprecated", NA))),
    show(pkg_lifecycle_statuses("lifecycle", which = "questioning")),
    sep = " || "
  )
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
shown <- enc2utf8(paste(as.character(value), collapse = "|"))
shown <- gsub("\n", " / ", shown, fixed = TRUE)
cat("VALUE ", shown, "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
