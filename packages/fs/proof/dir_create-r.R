
suppressPackageStartupMessages(library(fs))
emit <- function(x) {
  if (is.null(x)) return("null")
  if (inherits(x, "fs_perms")) x <- as.integer(x)
  if (inherits(x, "fs_bytes")) x <- as.numeric(x)
  if (is.factor(x)) x <- as.character(x)
  if (is.logical(x)) {
    parts <- ifelse(is.na(x), "null", ifelse(x, "true", "false"))
    return(paste0("[", paste(parts, collapse = ","), "]"))
  }
  if (is.numeric(x)) {
    parts <- ifelse(is.na(x), "null", sprintf("%.17g", x))
    return(paste0("[", paste(parts, collapse = ","), "]"))
  }
  if (is.character(x)) {
    parts <- vapply(x, function(item) {
      if (is.na(item)) return("null")
      item <- gsub("\\", "\\\\", item, fixed = TRUE)
      item <- gsub("\"", "\\\"", item, fixed = TRUE)
      paste0("\"", item, "\"")
    }, "")
    return(paste0("[", paste(parts, collapse = ","), "]"))
  }
  if (is.list(x)) {
    return(paste0("[", paste(vapply(x, emit, ""), collapse = ","), "]"))
  }
  "null"
}

one <- function() {

  root <- tempfile("fsproof")
  dir_create(root)
  dir_create(path(root, "d/sub"))
  file_create(path(root, c("d/a.txt", "d/sub/b.txt")))
  link_create(path_abs(path(root, "d/a.txt")), path(root, "d/link"))

  dir_create(path(root, "fresh/nested"))
  dir_exists(path(root, "fresh/nested"))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("{\"value\":%s,\"median_ms\":%.17g}\n", emit(value), median(elapsed) * 1000))
