.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(remotes))
stopifnot(identical(as.character(packageVersion("remotes")), "2.5.0"))

url <- "https://cran.r-project.org"
db <- c(Package = "digest", Version = "0.6.37")
insert <- function() available_packages_set(url, "source", db)
one <- function() available_packages_reset()

invisible(insert())
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  insert()
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

stopifnot(is.null(value))
fresh <- available_packages_set(url, "source", c(Package = "kept"))
stopifnot(identical(unname(fresh), "kept"))

cat(sprintf("{\"value\":null,\"median_ms\":%.17g}\n", median(elapsed) * 1000))
