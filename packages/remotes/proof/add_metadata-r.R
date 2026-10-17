.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(remotes))

json_str <- function(s) {
  if (length(s) == 0 || is.na(s)) return("null")
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

pkg <- tempfile("addmeta")
dir.create(file.path(pkg, "Meta"), recursive = TRUE)
rds <- file.path(pkg, "Meta", "package.rds")
saveRDS(
  structure(list(DESCRIPTION = c(Package = "foo", Version = "1.0.0")), class = "packageDescription2"),
  rds
)
meta <- list(RemoteType = "github", RemoteRepo = "foo")
add_metadata(pkg, meta)
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  add_metadata(pkg, meta)
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
desc <- readRDS(rds)$DESCRIPTION
text <- paste(sprintf("%s=%s", names(desc), desc), collapse = "\n")
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', json_str(text), median(elapsed) * 1000))
