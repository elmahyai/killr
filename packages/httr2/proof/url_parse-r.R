.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(httr2))
fmt <- function(x) if (is.null(x)) "NULL" else as.character(x)
one <- function() {
  u <- url_parse("http://user:pass@example.com:81/path?a=1&b=2&c={1{2}3}#frag")
  query <- if (is.null(u$query)) "NULL" else paste(names(u$query), unlist(u$query, use.names = FALSE), sep = "=", collapse = "&")
  paste(paste(class(u), collapse = "/"), fmt(u$scheme), fmt(u$hostname), fmt(u$username), fmt(u$password), fmt(u$port), fmt(u$path), query, fmt(u$fragment), sep = "|")
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
