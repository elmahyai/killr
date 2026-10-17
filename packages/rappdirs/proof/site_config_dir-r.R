suppressPackageStartupMessages(library(rappdirs))
stopifnot(identical(as.character(packageVersion("rappdirs")), "0.3.4"))

json_str <- function(s) {
  if (length(s) != 1 || is.na(s)) return("null")
  s <- enc2utf8(s)
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub('"', '\\"', s, fixed = TRUE)
  s <- gsub("\n", "\\n", s, fixed = TRUE)
  s <- gsub("\r", "\\r", s, fixed = TRUE)
  paste0('"', s, '"')
}

one <- function() {
  c(
    site_config_dir("rappdirs"),
    site_config_dir("R", os = "mac"),
    site_config_dir("R", os = "win", appauthor = "Posit"),
    site_config_dir("rappdirs", os = "unix"),
    site_config_dir("rappdirs", os = "unix", multipath = TRUE),
    site_config_dir("app", version = "%V"),
    site_config_dir("app", version = "%v"),
    site_config_dir(NULL),
    site_config_dir(""),
    site_config_dir(c("a", "b"))
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  '{"value":[%s],"median_ms":%.17g}\n',
  paste(vapply(value, json_str, ""), collapse = ","),
  median(elapsed) * 1000
))
