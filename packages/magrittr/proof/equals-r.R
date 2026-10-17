
.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(magrittr))

json_nums <- function(x) {
  parts <- character(length(x))
  for (i in seq_along(x)) {
    v <- x[[i]]
    parts[[i]] <- if (is.na(v)) "null" else sprintf("%.17g", as.numeric(v))
  }
  paste0("[", paste(parts, collapse = ","), "]")
}
json_logical <- function(x) {
  parts <- character(length(x))
  for (i in seq_along(x)) {
    v <- x[[i]]
    parts[[i]] <- if (is.na(v)) "null" else if (isTRUE(v)) "true" else "false"
  }
  paste0("[", paste(parts, collapse = ","), "]")
}
json_chars <- function(x) {
  parts <- character(length(x))
  for (i in seq_along(x)) {
    s <- x[[i]]
    parts[[i]] <- if (is.na(s)) "null" else sprintf("\"%s\"", s)
  }
  paste0("[", paste(parts, collapse = ","), "]")
}
json_list <- function(x) {
  parts <- character(length(x))
  for (i in seq_along(x)) {
    el <- x[[i]]
    if (is.logical(el)) parts[[i]] <- json_logical(el)
    else if (is.numeric(el) && length(el) == 1 && !is.na(el)) parts[[i]] <- sprintf("%.17g", as.numeric(el))
    else if (is.numeric(el)) parts[[i]] <- json_nums(el)
    else if (is.character(el) && length(el) == 1) parts[[i]] <- sprintf("\"%s\"", el)
    else parts[[i]] <- "null"
  }
  paste0("[", paste(parts, collapse = ","), "]")
}
json_obj <- function(extra) {
  parts <- character(length(extra))
  nms <- names(extra)
  for (i in seq_along(extra)) {
    el <- extra[[i]]
    encoded <- if (is.character(el) && length(el) == 1) sprintf("\"%s\"", el) else json_nums(el)
    parts[[i]] <- sprintf("\"%s\":%s", nms[[i]], encoded)
  }
  paste0("{", paste(parts, collapse = ","), "}")
}
emit <- function(value, median_ms) {
  names_json <- "null"
  values_json <- "null"
  cells_json <- "null"
  rownames_json <- "null"
  colnames_json <- "null"
  class_json <- "null"
  attr_json <- "null"
  if (is.matrix(value)) {
    rows <- character(nrow(value))
    for (i in seq_len(nrow(value))) rows[[i]] <- json_nums(value[i, ])
    cells_json <- paste0("[", paste(rows, collapse = ","), "]")
    if (!is.null(rownames(value))) rownames_json <- json_chars(rownames(value))
    if (!is.null(colnames(value))) colnames_json <- json_chars(colnames(value))
  } else if (is.list(value)) {
    values_json <- json_list(value)
    if (!is.null(names(value))) names_json <- json_chars(names(value))
  } else {
    values_json <- if (is.logical(value)) json_logical(value) else json_nums(value)
    if (!is.null(names(value))) names_json <- json_chars(names(value))
  }
  cls <- attr(value, "class")
  if (!is.null(cls)) class_json <- json_chars(cls)
  extra <- attributes(value)
  if (!is.null(extra)) {
    drop <- c("names", "class", "dim", "dimnames")
    extra <- extra[setdiff(names(extra), drop)]
    if (length(extra)) attr_json <- json_obj(extra)
  }
  cat(sprintf(
    "{\"names\":%s,\"values\":%s,\"cells\":%s,\"rownames\":%s,\"colnames\":%s,\"class\":%s,\"attr\":%s,\"median_ms\":%.17g}\n",
    names_json, values_json, cells_json, rownames_json, colnames_json, class_json, attr_json, median_ms
  ))
}

one <- function() {
  equals(c(1, 2, 3), c(1, 0, 3))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
out_dir <- "/home/ahmed/killr_projects/killr/packages/magrittr/docs/output"
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
writeLines("equals(c(1, 2), c(1, 0)) returns TRUE, FALSE.", file.path(out_dir, "equals-r.txt"))
emit(value, median(elapsed) * 1000)
