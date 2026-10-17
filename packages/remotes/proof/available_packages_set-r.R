.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(remotes))
stopifnot(identical(as.character(packageVersion("remotes")), "2.5.0"))

json_str <- function(s) {
  bytes <- as.integer(charToRaw(enc2utf8(s)))
  parts <- character(length(bytes))
  for (i in seq_along(bytes)) {
    b <- bytes[[i]]
    parts[[i]] <- if (b == 34) paste0("\\", '"')
      else if (b == 92) paste0("\\", "\\")
      else if (b == 10) paste0("\\", "n")
      else if (b == 13) paste0("\\", "r")
      else if (b == 9) paste0("\\", "t")
      else if (b < 32 || b == 127) sprintf("\\u%04x", b)
      else intToUtf8(b)
  }
  paste0('"', paste(parts, collapse = ""), '"')
}

json_chr <- function(x) {
  if (is.null(x)) return("null")
  if (length(x) == 0) return("[]")
  paste0("[", paste(vapply(unname(x), json_str, ""), collapse = ","), "]")
}

url <- "https://cran.r-project.org"
db <- c(Package = "digest", Version = "0.6.37")
one <- function() available_packages_set(url, "source", db)

available_packages_reset()
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  available_packages_reset()
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

second <- available_packages_set(url, "source", c(Package = "digest", Version = "9"))
stopifnot(identical(unname(second), unname(db)))

available_packages_reset()
fresh <- available_packages_set(url, "source", c(Package = "digest", Version = "9"))
stopifnot(identical(unname(fresh), c("digest", "9")))
held <- available_packages_set(url, "source", c(Package = "digest", Version = "0"))
stopifnot(identical(unname(held), c("digest", "9")))

named <- available_packages_set(c(CRAN = url), "source", c(Package = "other"))
stopifnot(identical(unname(named), "other"))
unnamed_again <- available_packages_set(url, "source", c(Package = "nope"))
stopifnot(identical(unname(unnamed_again), c("digest", "9")))

available_packages_reset()
null_db <- available_packages_set(url, "source", NULL)
replaced <- available_packages_set(url, "source", c(Package = "after-null"))
stopifnot(is.null(null_db))
stopifnot(identical(unname(replaced), "after-null"))

cat(sprintf(
  "{\"names\":%s,\"values\":%s,\"median_ms\":%.17g}\n",
  json_chr(names(value)),
  json_chr(unname(value)),
  median(elapsed) * 1000
))
