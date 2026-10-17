.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(fastmap))
if (packageDescription("fastmap")$Version != "1.2.0") stop("expected fastmap 1.2.0")

km <- key_missing()
plain <- fastmap()
sentinel <- fastmap(missing_default = km)

one <- function() {
  c(
    as.numeric(is.key_missing(km)),
    as.numeric(is.key_missing(NULL)),
    as.numeric(is.key_missing(1)),
    as.numeric(is.key_missing(list())),
    as.numeric(is.key_missing("key_missing")),
    as.numeric(is.key_missing(sentinel$get("absent"))),
    as.numeric(is.key_missing(plain$get("absent"))),
    as.numeric(is.key_missing(fastqueue()$remove())),
    as.numeric(is.key_missing(faststack(missing_default = km)$pop()))
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
parts <- sprintf("%.17g", value)
writeLines(
  sprintf(
    "{\"value\":[%s],\"median_ms\":%.17g}\n",
    paste(parts, collapse = ","),
    median(elapsed) * 1000
  ),
  con = "proof/is.key_missing-r.txt"
)

example <- paste0(
  "sentinel ", is.key_missing(km), "\n",
  "null ", is.key_missing(NULL), "\n",
  "number ", is.key_missing(1), "\n",
  "list ", is.key_missing(list()), "\n",
  "map ", is.key_missing(sentinel$get("absent")), "\n",
  "plain ", is.key_missing(plain$get("absent")), "\n",
  "stack ", is.key_missing(faststack(missing_default = km)$pop()), "\n"
)
cat(example, file = "docs/output/is.key_missing-r.txt")
