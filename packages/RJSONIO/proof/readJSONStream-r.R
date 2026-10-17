.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(jsonlite))
suppressPackageStartupMessages(library(RJSONIO))

show <- function(x) {
  if (is.null(x)) return("NULL")
  if (is.matrix(x)) {
    vals <- as.vector(x)
    text <- ifelse(is.na(vals), "NA", as.character(vals))
    return(paste0("matrix/", typeof(x), "[", nrow(x), "x", ncol(x), ":", paste(text, collapse = ","), "]"))
  }
  if (is.atomic(x)) {
    if (is.logical(x)) {
      vals <- ifelse(is.na(x), "NA", ifelse(x, "TRUE", "FALSE"))
    } else {
      vals <- ifelse(is.na(x), "NA", as.character(x))
    }
    nm <- if (is.null(names(x))) "" else paste0(" names=", paste(names(x), collapse = ","))
    return(paste0(paste(class(x), collapse = "+"), "/", typeof(x), "[", paste(vals, collapse = ","), "]", nm))
  }
  inner <- if (length(x) == 0) "" else paste(vapply(seq_along(x), function(j) show(x[[j]]), ""), collapse = " | ")
  nm <- if (is.null(names(x))) " nonames" else paste0(" names=", paste(names(x), collapse = ","))
  paste0("LIST{", inner, "}", nm, " class=", paste(class(x), collapse = "+"))
}

stream_file <- function(text) {
  path <- tempfile()
  cat(text, file = path)
  con <- file(path, open = "rb")
  on.exit({
    close(con)
    unlink(path)
  }, add = TRUE)
  readJSONStream(con)
}

stream_cb <- function(text) {
  path <- tempfile()
  cat(text, file = path)
  con <- file(path, open = "rb")
  on.exit({
    close(con)
    unlink(path)
  }, add = TRUE)
  readJSONStream(con, function(x) length(x))
}

one <- function() {
  parts <- c(
    show(stream_file("[1, 2, 3]")),
    show(stream_file("[1,2,3]{\"a\":[true,false]}")),
    show(stream_cb("[1,2,3]{\"a\":[true,false]}"))
  )
  paste(parts, collapse = "\n")
}

value <- one()
elapsed <- numeric(20)
for (step_i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[step_i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":%s,"median_ms":%.17g}\n', jsonlite::toJSON(value, auto_unbox = TRUE), median(elapsed) * 1000))
