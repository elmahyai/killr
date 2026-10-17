suppressPackageStartupMessages(library(purrr))
stopifnot(identical(as.character(packageVersion("purrr")), "1.2.2"))
options(lifecycle_verbosity = "quiet")

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
  if (is.factor(x)) {
    bits <- vapply(as.integer(x), function(s) {
      if (is.na(s)) "NA" else sprintf("%d", s)
    }, "")
    return(paste0(
      "F", paste(bits, collapse = ","),
      "L", paste(levels(x), collapse = ","),
      "{", enc_names(x), "}"
    ))
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

n <- 5000L
x <- vector("list", n)
nms <- character(n)
for (i in seq_len(n)) {
  if (i %% 17L == 0L) {
    nms[[i]] <- ""
  } else if (i %% 19L == 0L) {
    nms[[i]] <- NA_character_
  } else {
    nms[[i]] <- paste0("p", i)
  }
  r <- i %% 11L
  if (r == 0L) {
    x[i] <- list(NULL)
  } else if (r == 1L) {
    x[[i]] <- c(a = i / 3, b = -0)
  } else if (r == 2L) {
    x[[i]] <- c(x = i, y = NA_integer_, z = i %% 7L)
  } else if (r == 3L) {
    x[[i]] <- c(TRUE, FALSE, NA)
  } else if (r == 4L) {
    x[[i]] <- c(s = paste0("v", i), t = NA_character_)
  } else if (r == 5L) {
    x[[i]] <- if (i %% 2L == 0L) i / 7 else NA_real_
  } else if (r == 6L) {
    x[[i]] <- list(list(i), NULL, i + 0.5)
  } else if (r == 7L) {
    x[[i]] <- as.raw(c(i %% 256L, 255L))
  } else if (r == 8L) {
    x[[i]] <- complex(real = -0, imaginary = i)
  } else if (r == 9L) {
    x[[i]] <- numeric(0)
  } else {
    x[[i]] <- c(NaN, Inf, -Inf, i / 11)
  }
}
names(x) <- nms

manual <- list(list(1, 2), list(3, 4))
names_case <- list(a = list(x = 1), b = 2:3, c = NULL)
scalar_parent <- list(a = list(1), b = list(2))
child <- list(a = list(x = 1), b = list(y = 2))
blank <- list(structure(numeric(0), names = character(0)), 1)
na_child <- list(c(a = 1), structure(2, names = NA_character_))
parent_na <- setNames(list(1, c(z = 2)), c(NA, "b"))
long_scalar <- list(a = 1:2, b = 3)
no_names <- list(1:2, 3:4)
nested_null <- list(list(1, NULL, 2))
factor_direct <- list(factor(c("b", "a")))
factor_kept <- list(list(factor(c("b", "a"))))
columns <- data.frame(a = 1:2, b = 3:4)
inner_named <- list(list(c(a = 1, b = 2)))
empty <- list()
nulls <- list(NULL, NULL)
only_empty_named <- list(structure(numeric(0), names = character(0)))
special <- list(
  c(a = NA_real_, b = NaN, c = Inf, d = -Inf),
  NA_complex_,
  as.raw(c(0L, 255L)),
  NA_character_,
  c(TRUE, NA)
)

one <- function() {
  list(
    manual = flatten(manual),
    names_case = flatten(names_case),
    scalar_parent = flatten(scalar_parent),
    child = flatten(child),
    blank = flatten(blank),
    na_child = flatten(na_child),
    parent_na = flatten(parent_na),
    long_scalar = flatten(long_scalar),
    no_names = flatten(no_names),
    nested_null = flatten(nested_null),
    factor_direct = flatten(factor_direct),
    factor_kept = flatten(factor_kept),
    columns = flatten(columns),
    inner_named = flatten(inner_named),
    empty = flatten(empty),
    nulls = flatten(nulls),
    only_empty_named = flatten(only_empty_named),
    special = flatten(special),
    big = flatten(x)
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
  encode(value$manual),
  encode(value$names_case),
  encode(value$scalar_parent),
  encode(value$child),
  encode(value$blank),
  encode(value$na_child),
  encode(value$parent_na),
  encode(value$long_scalar),
  encode(value$no_names),
  encode(value$nested_null),
  encode(value$factor_direct),
  encode(value$factor_kept),
  encode(value$columns),
  encode(value$inner_named),
  encode(value$empty),
  encode(value$nulls),
  encode(value$only_empty_named),
  encode(value$special),
  encode(value$big),
  sep = " "
)
cat("VALUE ", shown, "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))
