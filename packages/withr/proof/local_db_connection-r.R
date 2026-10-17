suppressPackageStartupMessages(library(withr))
suppressPackageStartupMessages({library(DBI); library(RSQLite)})

json_escape <- function(x) {
  x <- gsub("\\", "\\\\", x, fixed = TRUE)
  x <- gsub("\"", "\\\"", x, fixed = TRUE)
  x <- gsub("\n", "\\n", x, fixed = TRUE)
  x <- gsub("\r", "\\r", x, fixed = TRUE)
  paste0("\"", x, "\"")
}
to_json <- function(x) {
  if (is.null(x)) return("null")
  if (is.list(x)) {
    return(paste0("[", paste(vapply(x, to_json, ""), collapse = ","), "]"))
  }
  if (is.logical(x)) {
    bits <- ifelse(is.na(x), "null", ifelse(x, "true", "false"))
    if (length(bits) == 1) return(bits)
    return(paste0("[", paste(bits, collapse = ","), "]"))
  }
  if (is.character(x)) {
    if (length(x) == 1) return(json_escape(x))
    return(paste0("[", paste(vapply(x, json_escape, ""), collapse = ","), "]"))
  }
  if (is.numeric(x)) {
    if (length(x) == 1) return(sprintf("%.17g", x))
    return(paste0("[", paste(sprintf("%.17g", x), collapse = ","), "]"))
  }
  stop(paste("unsupported", paste(class(x), collapse = ",")))
}
one <- function() {
  con <- DBI::dbConnect(RSQLite::SQLite(), ":memory:")
  DBI::dbExecute(con, "CREATE TABLE t (x REAL)")
  DBI::dbExecute(con, "INSERT INTO t VALUES (1), (2)")
  result <- local({
    con <- local_db_connection(con)
    DBI::dbGetQuery(con, "SELECT SUM(x) AS s FROM t")$s
  })
  list(result, !DBI::dbIsValid(con))
}
value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("{\"value\":%s,\"median_ms\":%.17g}\n", to_json(value), median(elapsed) * 1000))
