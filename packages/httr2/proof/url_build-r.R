.libPaths(c("/home/ahmed/R/curl-8.1.0", "/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(httr2))
stopifnot(identical(as.character(packageVersion("httr2")), "1.3.0"))
stopifnot(packageVersion("curl") >= "6.4.0")
one <- function() {
  url_build(url_parse("http://user:pass@example.com:81/a:b/foo%20bar/?a=1&b=2&c={1{2}3}#frag"))
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
