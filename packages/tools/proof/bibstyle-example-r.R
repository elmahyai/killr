suppressPackageStartupMessages(library(tools))
invisible(
  bibstyle(
    "unsorted",
    sortKeys = function(refs) seq_along(refs),
    fmtPrefix = function(paper) paste0("[", paper$.index, "]"),
    .init = TRUE
  )
)
env <- bibstyle("unsorted", .default = FALSE)
cat(paste0(paste(env$sortKeys(list(list(), list())), collapse = ","), "\n"))
cat(paste0(env$fmtPrefix(list(.index = 1)), "\n"))
