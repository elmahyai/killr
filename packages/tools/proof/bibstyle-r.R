suppressPackageStartupMessages(library(tools))

one <- function() {
  parts <- character()
  jss <- bibstyle()
  parts <- c(parts, paste(sort(ls(envir = jss)), collapse = ","))
  bibstyle(
    "unsorted",
    sortKeys = function(refs) seq_along(refs),
    fmtPrefix = function(paper) paste0("[", paper$.index, "]"),
    .init = TRUE,
    .default = FALSE
  )
  uns <- bibstyle("unsorted", .default = FALSE)
  sk <- uns$sortKeys(list(list(), list()))
  parts <- c(parts, paste(sk, collapse = ","))
  parts <- c(parts, uns$fmtPrefix(list(.index = 3)))
  parts <- c(parts, getBibstyle())
  paste0(paste(parts, collapse = "\n"), "\n")
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(value, sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
