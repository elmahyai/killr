.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(remotes))
stopifnot(identical(as.character(packageVersion("remotes")), "2.5.0"))

url <- "https://cloud.r-project.org"
available_packages_reset()
db <- available_packages(url, "source")
hit <- match("remotes", rownames(db))
stopifnot(!is.na(hit))
pkg <- unname(db[hit, "Package"])
ver <- unname(db[hit, "Version"])
rn <- rownames(db)[hit]
n <- nrow(db)

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  available_packages(url, "source")
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

named <- available_packages_set(c(CRAN = url), "source", c(Package = "other"))
stopifnot(identical(unname(named), "other"))
again <- available_packages(url, "source")
stopifnot(identical(unname(again["remotes", "Version"]), ver))
stopifnot(identical(nrow(again), n))

cat(sprintf(
  "{\"package\":\"%s\",\"version\":\"%s\",\"rowname\":\"%s\",\"nrow\":%d,\"median_ms\":%.17g}\n",
  pkg, ver, rn, n, median(elapsed) * 1000
))
