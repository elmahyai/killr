.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(curl))
one <- function() {
  u <- curl_parse_url("https://jerry:secret@google.com:888/foo/bar?test=123#bla"); paste(u$url, u$scheme, u$host, u$port, u$path, u$user, u$password, u$fragment, paste(names(u$params), u$params, sep = "="), sep = "|")
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
