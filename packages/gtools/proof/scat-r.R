.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(gtools))
stopifnot(as.character(packageVersion("gtools")) == "3.9.5")

json_str <- function(s) {
  chars <- strsplit(enc2utf8(s), "")[[1]]
  parts <- character(length(chars))
  for (i in seq_along(chars)) {
    cp <- utf8ToInt(chars[[i]])
    parts[[i]] <- if (cp == 34) paste0("\\", '"')
      else if (cp == 92) paste0("\\", "\\")
      else if (cp == 10) paste0("\\", "n")
      else if (cp == 13) paste0("\\", "r")
      else if (cp == 9) paste0("\\", "t")
      else if (cp < 32 || cp == 127) sprintf("\\u%04x", cp)
      else chars[[i]]
  }
  paste0('"', paste(parts, collapse = ""), '"')
}

flat <- function(x) {
  paste(vapply(x, json_str, ""), collapse = ",")
}

capture_scat <- function(...) {
  tf <- tempfile()
  con <- file(tf, open = "wt")
  sink(con, type = "message")
  on.exit({ sink(type = "message"); close(con) })
  scat(...)
  sz <- file.info(tf)$size
  if (is.na(sz) || sz == 0) {
    return("")
  }
  readChar(tf, sz)
}

one <- function() {
  options(DEBUG = NULL)
  out <- character(0)
  out[[1]] <- capture_scat("Not displayed")
  options(DEBUG = TRUE)
  out[[2]] <- capture_scat(
    "This will be displayed immediately (even in R BATCH output \n"
  )
  out[[3]] <- capture_scat("files), provided options()$DEBUG is TRUE.")
  out[[4]] <- capture_scat("a", "b", "c")
  out[[5]] <- capture_scat(1, 2, 3)
  out[[6]] <- capture_scat(TRUE, FALSE)
  out[[7]] <- capture_scat(c("x", "y"))
  options(DEBUG = FALSE)
  out[[8]] <- capture_scat("hidden")
  options(DEBUG = TRUE)
  out[[9]] <- capture_scat("line1\n", "line2")
  out[[10]] <- capture_scat("num ", pi, " end")
  out[[11]] <- capture_scat(1 / 7, 2 / 7, 3 / 7)
  out[[12]] <- capture_scat("mix", c("p", "q"), 42)
  out[[13]] <- capture_scat(NaN, Inf, -Inf, NA)
  out[[14]] <- capture_scat(1 + 2i)
  options(DEBUG = 1)
  out[[15]] <- capture_scat("numeric TRUE")
  options(DEBUG = 0)
  out[[16]] <- capture_scat("numeric FALSE")
  out
}

invisible <- one()
value <- flat(one())
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf('{"value":[%s],"median_ms":%.17g}\n', value, median(elapsed) * 1000))
