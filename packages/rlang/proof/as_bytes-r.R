.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(rlang))
if (as.character(packageVersion("rlang")) != "1.3.0") {
  stop("expected rlang 1.3.0")
}
fmt <- function(v) sprintf("%.17g", v)

one <- function() {
  num <- as_bytes(c(1000, 2500000))
  chr <- as_bytes(c("1MB", "500KB", "1K"))
  total <- sum(as_bytes(c("1MB", "5MB", "500KB")))
  paste(
    paste(fmt(unclass(num)), collapse = ","),
    paste(fmt(unclass(chr)), collapse = ","),
    fmt(unclass(total)),
    as.character(identical(as_bytes(num), num)),
    sep = "|"
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
