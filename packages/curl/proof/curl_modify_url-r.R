.libPaths(c("/home/ahmed/R/curl-8.1.0", path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(curl))
stopifnot(identical(as.character(packageVersion("curl")), "8.1.0"))
one <- function() {
  url <- "https://jerry:secret@google.com:888/foo/bar?test=123#bla"
  out <- curl_parse_url(url)
  curl_modify_url(out)
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
