.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(remotes))
one <- function() bioc_install_repos(bioc_ver = "3.6")
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
pairs <- vapply(seq_along(value), function(i) {
  sprintf('["%s","%s"]', names(value)[[i]], value[[i]])
}, "")
cat(sprintf(
  '{"value":[%s],"median_ms":%.17g}\n',
  paste(pairs, collapse = ","),
  median(elapsed) * 1000
))
