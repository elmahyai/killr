suppressPackageStartupMessages(library(purrr))
stopifnot(identical(as.character(packageVersion("purrr")), "1.2.2"))

n <- 4000L
x <- vector("list", n)
for (i in seq_len(n)) {
  if (i %% 5L == 0L) {
    x[i] <- list(NULL)
  } else if (i %% 7L == 0L) {
    x[[i]] <- numeric(0)
  } else if (i %% 11L == 0L) {
    x[[i]] <- NA_real_
  } else if (i %% 13L == 0L) {
    x[[i]] <- NaN
  } else if (i %% 17L == 0L) {
    x[[i]] <- c(0, Inf, -Inf)
  } else {
    x[[i]] <- c(i / 3, (i %% 11) / 7)
  }
}
names(x) <- paste0("v", seq_len(n))

encode_num <- function(v) {
  if (is.na(v) && !is.nan(v)) {
    "NA"
  } else if (is.nan(v)) {
    "NaN"
  } else if (is.infinite(v)) {
    if (v > 0) "Inf" else "-Inf"
  } else {
    sprintf("%.17g", v)
  }
}

encode_ex <- function(ex) {
  d_txt <- if (is.logical(ex$d) && length(ex$d) == 1L && is.na(ex$d)) "NA" else "BAD"
  paste0(
    "a:", typeof(ex$a), ":", ex$a,
    "|d:", typeof(ex$d), ":", d_txt,
    "|n:", length(ex),
    "|names:", paste(names(ex), collapse = ",")
  )
}

encode_big <- function(value) {
  parts <- vapply(seq_along(value), function(i) {
    el <- value[[i]]
    bits <- vapply(seq_along(el), function(j) encode_num(el[[j]]), "")
    paste0(names(value)[[i]], ":", paste(bits, collapse = ","))
  }, "")
  paste(parts, collapse = ";")
}

one <- function() {
  ex <- compact(list(a = "a", b = NULL, c = integer(0), d = NA, e = list()))
  big <- compact(x)
  list(ex = ex, big = big)
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
shown <- paste0("EX ", encode_ex(value$ex), " BIG ", encode_big(value$big))
cat("VALUE ", shown, "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
