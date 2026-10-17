.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(gtools))
stopifnot(as.character(packageVersion("gtools")) == "3.9.5")

clear_last <- function() {
  if (exists(".Last", envir = .GlobalEnv, inherits = FALSE)) {
    rm(.Last, envir = .GlobalEnv)
  }
}

one <- function() {
  on.exit(clear_last(), add = TRUE)
  clear_last()
  logs <- character()
  bye <- function() {
    logs <<- c(logs, "bye")
    1
  }
  hello <- function() {
    logs <<- c(logs, "hello")
    2
  }
  early <- function() {
    logs <<- c(logs, "early")
    3
  }

  parts <- character()
  f0 <- lastAdd(bye)
  parts <- c(parts, if (identical(f0, bye)) "SAME" else "DIFF", as.character(f0()))

  assign(".Last", bye, envir = .GlobalEnv)
  f1 <- lastAdd(hello)
  parts <- c(parts, if (identical(f1, hello)) "SAME" else "WRAP", as.character(f1(9)))

  other <- function() {
    logs <<- c(logs, "other")
    9
  }
  assign(".Last", other, envir = .GlobalEnv)
  parts <- c(parts, as.character(f1()))

  assign(".Last", f1, envir = .GlobalEnv)
  f2 <- lastAdd(early)
  parts <- c(parts, as.character(f2()))

  assign(".Last", 5, envir = .GlobalEnv)
  parts <- c(parts, if (identical(lastAdd(hello), hello)) "NUM_SAME" else "NUM_WRAP")
  assign(".Last", NULL, envir = .GlobalEnv)
  parts <- c(parts, if (identical(lastAdd(hello), hello)) "NULL_SAME" else "NULL_WRAP")
  assign(".Last", list(hello), envir = .GlobalEnv)
  parts <- c(parts, if (identical(lastAdd(hello), hello)) "LIST_SAME" else "LIST_WRAP")

  clear_last()
  local_same <- local({
    .Last <- function() 99
    identical(lastAdd(hello), hello)
  })
  parts <- c(parts, if (isTRUE(local_same)) "LOCAL_IGNORED" else "LOCAL_SEEN")

  hit <- 0
  bad <- function() stop("boom")
  good <- function() {
    hit <<- hit + 1
    4
  }
  assign(".Last", good, envir = .GlobalEnv)
  err <- tryCatch(lastAdd(bad)(), error = function(e) conditionMessage(e))
  parts <- c(parts, err, as.character(hit))
  parts <- c(
    parts,
    tryCatch(lastAdd(1), error = function(e) conditionMessage(e)),
    tryCatch(lastAdd(NULL), error = function(e) conditionMessage(e)),
    tryCatch(lastAdd("x"), error = function(e) conditionMessage(e)),
    tryCatch(lastAdd(list(hello)), error = function(e) conditionMessage(e))
  )

  clear_last()
  helloWorld <- function() cat("\nHello World!\n")
  byeWorld <- function() cat("\nGoodbye World!\n")
  assign(".Last", lastAdd(byeWorld), envir = .GlobalEnv)
  assign(".Last", lastAdd(helloWorld), envir = .GlobalEnv)
  raw_con <- rawConnection(raw(0), open = "w")
  sink(raw_con)
  ex_val <- .Last()
  sink()
  printed <- rawToChar(rawConnectionValue(raw_con))
  close(raw_con)
  parts <- c(parts, if (is.null(ex_val)) "NULL" else as.character(ex_val), printed)
  parts <- c(parts, paste(logs, collapse = ","))
  paste(parts, collapse = "|")
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
esc <- function(s) {
  s <- enc2utf8(s)
  s <- gsub("\\", "\\\\", s, fixed = TRUE)
  s <- gsub('"', '\\"', s, fixed = TRUE)
  s <- gsub("\n", "\\n", s, fixed = TRUE)
}
cat(sprintf('{"value":"%s","median_ms":%.17g}\n', esc(value), median(elapsed) * 1000))
