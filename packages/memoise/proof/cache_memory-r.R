.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(memoise))
json_num <- function(x) {
  parts <- sprintf("%.17g", as.numeric(x))
  if (length(parts) == 1) return(parts[[1]])
  paste0("[", paste(parts, collapse = ","), "]")
}

one <- function() {
  cm <- cache_memory()
  cm$set("k", 7)
  got <- cm$get("k")
  has <- cm$has_key("k")
  cm$drop_key("k")
  has2 <- cm$has_key("k")
  cm$set("a", 1)
  cm$reset()
  c(got, as.integer(has), as.integer(has2), length(cm$keys()))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_num(value), median(elapsed) * 1000))
