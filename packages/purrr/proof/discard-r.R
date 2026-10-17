suppressPackageStartupMessages(library(purrr))
stopifnot(identical(as.character(packageVersion("purrr")), "1.2.2"))

n <- 8000L
x <- numeric(n)
for (i in seq_len(n)) {
  r <- i %% 17L
  if (r == 0L) {
    x[[i]] <- NA_real_
  } else if (r == 1L) {
    x[[i]] <- NaN
  } else if (r == 2L) {
    x[[i]] <- Inf
  } else if (r == 3L) {
    x[[i]] <- -Inf
  } else if (r == 4L) {
    x[[i]] <- -0
  } else {
    x[[i]] <- (i %% 97L) / 7
  }
}
names(x) <- paste0("v", seq_len(n))

enc_real <- function(v) {
  if (is.na(v) && !is.nan(v)) {
    "NA"
  } else if (is.nan(v)) {
    "NaN"
  } else if (is.infinite(v)) {
    if (v > 0) "Inf" else "-Inf"
  } else if (v == 0 && sign(1 / v) < 0) {
    "-0"
  } else {
    sprintf("%.17g", v)
  }
}

enc_names <- function(value) {
  if (is.null(names(value))) {
    "*"
  } else if (!length(names(value))) {
    ""
  } else {
    paste(vapply(names(value), function(nm) {
      if (is.na(nm)) "NA" else if (!nzchar(nm)) "E" else paste0("S", nm)
    }, ""), collapse = ",")
  }
}

encode_ex <- function(ex) {
  el <- ex[[1]]
  paste0(
    "L(", enc_names(ex), "){L(", enc_names(el), "){",
    "logical(*)[", if (is.na(el$a)) "NA" else if (el$a) "TRUE" else "FALSE", "];",
    "integer(*)[", paste(el$b, collapse = ","), "]}}"
  )
}

encode_mask <- function(value) {
  paste0(
    "double(", enc_names(value), ")[",
    paste(vapply(value, enc_real, ""), collapse = ","),
    "]"
  )
}

encode_extra <- function(value) {
  paste0("integer(", enc_names(value), ")[", paste(value, collapse = ","), "]")
}

encode_chr <- function(value) {
  body <- paste(vapply(value, function(s) if (is.na(s)) "NA" else paste0("S", s), ""), collapse = ",")
  paste0("character(", enc_names(value), ")[", body, "]")
}

encode_big <- function(value) {
  parts <- vapply(seq_along(value), function(i) {
    paste0(names(value)[[i]], ":", enc_real(value[[i]]))
  }, "")
  paste(parts, collapse = ";")
}

one <- function() {
  ex <- discard(list(
    list(a = TRUE, b = 4:6),
    list(a = FALSE, b = 7:9),
    list(a = TRUE, b = 1:3)
  ), "a")
  mask <- discard(c(a = 1, b = -0, c = NA, d = 4), c(TRUE, FALSE, NA, TRUE))
  extra <- discard(1:6, function(v, lim) v > lim, 3)
  chars <- discard(c(a = "x", b = "y", c = ""), function(s) nzchar(s))
  big <- discard(x, function(v) is.finite(v) && v > 5)
  list(ex = ex, mask = mask, extra = extra, chars = chars, big = big)
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
shown <- paste0(
  "EX ", encode_ex(value$ex),
  " MASK ", encode_mask(value$mask),
  " EXTRA ", encode_extra(value$extra),
  " CHR ", encode_chr(value$chars),
  " BIG ", encode_big(value$big)
)
cat("VALUE ", shown, "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
