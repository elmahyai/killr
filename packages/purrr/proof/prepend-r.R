suppressPackageStartupMessages(library(purrr))
stopifnot(identical(as.character(packageVersion("purrr")), "1.2.2"))

enc_name <- function(nm) {
  if (is.na(nm)) {
    "NA"
  } else if (!nzchar(nm)) {
    "E"
  } else {
    paste0("S", nm)
  }
}

enc_names <- function(x) {
  if (is.null(names(x))) {
    "*"
  } else {
    paste(vapply(names(x), enc_name, ""), collapse = ",")
  }
}

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

encode <- function(x) {
  if (is.null(x)) {
    return("NULL")
  }
  if (is.list(x)) {
    if (length(x) == 0) {
      els <- ""
    } else {
      els <- paste(vapply(seq_along(x), function(i) {
        el <- x[[i]]
        if (is.null(el)) "NULL" else encode(el)
      }, ""), collapse = "|")
    }
    return(paste0("L{", enc_names(x), "}:", els))
  }
  if (is.character(x)) {
    bits <- vapply(x, function(s) if (is.na(s)) "NA" else paste0("S", s), "")
    return(paste0("C", paste(bits, collapse = ","), "{", enc_names(x), "}"))
  }
  if (is.logical(x)) {
    bits <- vapply(x, function(s) {
      if (is.na(s)) "NA" else if (isTRUE(s)) "T" else "F"
    }, "")
    return(paste0("G", paste(bits, collapse = ","), "{", enc_names(x), "}"))
  }
  if (is.integer(x)) {
    bits <- vapply(x, function(s) if (is.na(s)) "NA" else sprintf("%d", s), "")
    return(paste0("I", paste(bits, collapse = ","), "{", enc_names(x), "}"))
  }
  if (is.complex(x)) {
    bits <- vapply(seq_along(x), function(i) {
      z <- x[[i]]
      if (is.na(z)) "NA" else paste0(enc_real(Re(z)), "+", enc_real(Im(z)))
    }, "")
    return(paste0("Z", paste(bits, collapse = ","), "{", enc_names(x), "}"))
  }
  if (is.raw(x)) {
    return(paste0(
      "X", paste(sprintf("%02x", as.integer(x)), collapse = ","),
      "{", enc_names(x), "}"
    ))
  }
  paste0("D", paste(vapply(x, enc_real, ""), collapse = ","), "{", enc_names(x), "}")
}

n <- 100000L
big <- seq_len(n) / 3
names(big) <- paste0("v", seq_len(n))
special <- c(a = -0, b = NA_real_, c = NaN, d = Inf, e = -Inf, f = 1.5)

one <- function() {
  ex_a <- prepend(as.list(1:3), "a")
  ex_b <- prepend(as.list(1:3), list("a", "b"), before = 3)
  ex_c <- prepend(list(), as.list(1:3))
  front <- prepend(c(p = 1L, q = 2L, r = 3L), c(TRUE, FALSE, NA))
  chars <- prepend("z", c(1e-4, 1e5, 1 / 3, NA_real_, NaN, Inf))
  comp <- prepend(c(1 + 2i, 1 - 2i), 0 + 1i)
  rawv <- prepend(as.raw(c(0, 15)), as.raw(255))
  lst <- prepend(list(a = 1, b = NULL, c = "q"), list(d = 2L), before = 2L)
  frac <- prepend(1:5, 99, before = 1.9)
  sign <- prepend(c(-0, 1), -0)
  mid <- prepend(big, special, before = n %/% 2L)
  list(
    ex_a = ex_a, ex_b = ex_b, ex_c = ex_c, front = front, chars = chars,
    comp = comp, rawv = rawv, lst = lst, frac = frac, sign = sign, mid = mid
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

shown <- paste(
  encode(value$ex_a), encode(value$ex_b), encode(value$ex_c),
  encode(value$front), encode(value$chars), encode(value$comp),
  encode(value$rawv), encode(value$lst), encode(value$frac),
  encode(value$sign), encode(value$mid),
  sep = " "
)
cat("VALUE ", shown, "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
