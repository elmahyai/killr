.libPaths(c("/home/ahmed/R/curl-8.1.0", path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(curl))
stopifnot(identical(as.character(packageVersion("curl")), "8.1.0"))
one <- function() {
  tbl <- curl_options_table("^url$")
  paste(tbl$name, tbl$value, as.character(tbl$type), sep = "=", collapse = "|")
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
