suppressPackageStartupMessages(library(survival))

case_a <- function() {
  structure(list(
    n = 5L,
    time = c(1, 2, 4, 7),
    n.risk = c(5, 4, 3, 1),
    n.event = c(1, 0, 1, 1),
    n.censor = c(0, 1, 1, 0),
    surv = c(0.8, 0.8, 0.4, 0.2),
    std.err = c(0.1, 0.1, 0.2, 0.3),
    upper = c(0.95, 0.95, 0.7, 0.6),
    lower = c(0.6, 0.6, 0.2, 0.1),
    influence.surv = matrix(c(0.1, -0.2, 0.3, 0.4, -0.5, 0.6, 0.7, -0.8), nrow = 2),
    logse = TRUE,
    conf.int = 0.95,
    conf.type = "log",
    time0 = FALSE,
    type = "right"
  ), class = "survfit")
}

case_b <- function() {
  x <- case_a()
  x$influence.surv <- NULL
  x$cumhaz <- c(0.2231, 0.2231, 0.9163, 1.6094)
  x$logse <- FALSE
  x
}

case_c <- function() {
  structure(list(
    n = c(3L, 2L),
    time = c(1, 2, 4, 0, 3),
    n.risk = c(5, 4, 2, 2, 1),
    n.event = c(1, 0, 1, 0, 1),
    n.censor = c(0, 1, 0, 1, 0),
    surv = c(0.8, 0.8, 0.4, 1, 0.5),
    std.err = c(0.1, 0.1, 0.2, 0, 0.3),
    cumhaz = c(0.2231, 0.2231, 0.9163, 0, 0.6931),
    strata = c(3L, 2L),
    logse = TRUE,
    conf.type = "log",
    type = "right"
  ), class = "survfit")
}

case_d <- function() {
  structure(list(
    n = c(2L, 3L),
    time = c(1, 2, 3, 5, 6),
    n.risk = c(5, 4, 3, 2, 1),
    n.event = c(1, 0, 1, 0, 1),
    n.censor = c(0, 1, 0, 1, 0),
    surv = c(0.8, 0.8, 0.5, 0.5, 0.25),
    std.err = c(0.1, 0.1, 0.2, 0.2, 0.3),
    strata = c(2L, 3L),
    logse = TRUE,
    conf.type = "log",
    type = "right"
  ), class = "survfit")
}

case_e <- function() {
  structure(list(
    n = 6L,
    time = c(1, 2, 4, 7),
    n.risk = c(6, 5, 3, 2),
    n.event = c(1, 0, 1, 1),
    n.censor = c(0, 1, 0, 0),
    surv = matrix(c(0.9, 0.9, 0.6, 0.5, 0.8, 0.7, 0.5, 0.4), nrow = 4),
    std.err = matrix(c(0.05, 0.05, 0.1, 0.12, 0.06, 0.07, 0.11, 0.13), nrow = 4),
    cumhaz = matrix(c(0.105, 0.105, 0.51, 0.69, 0.22, 0.36, 0.69, 0.92), nrow = 4),
    upper = matrix(c(0.97, 0.97, 0.8, 0.7, 0.95, 0.9, 0.8, 0.7), nrow = 4),
    lower = matrix(c(0.8, 0.8, 0.4, 0.3, 0.6, 0.5, 0.3, 0.2), nrow = 4),
    logse = TRUE,
    type = "right"
  ), class = "survfit")
}

case_f <- function() {
  structure(list(
    n = c(3L, 2L),
    time = c(1, 2, 4, 0, 3),
    n.risk = matrix(c(4, 3, 1, 2, 1, 0, 1, 2, 0, 1), nrow = 5),
    n.event = matrix(c(1, 0, 1, 0, 0, 0, 1, 0, 1, 1), nrow = 5),
    pstate = array(c(0.02, 0.04, 0.06, 0.08, 0.10, 0.12, 0.14, 0.16, 0.18, 0.20,
                     0.22, 0.24, 0.26, 0.28, 0.30, 0.32, 0.34, 0.36, 0.38, 0.40),
                   dim = c(5, 2, 2)),
    p0 = matrix(c(0.9, 0.8, 0.1, 0.2), nrow = 2),
    sp0 = matrix(c(0.01, 0.02, 0.03, 0.04), nrow = 2),
    cumhaz = matrix(c(0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9, 1.0), nrow = 5),
    std.err = matrix(c(0.01, 0.02, 0.03, 0.04, 0.05, 0.06, 0.07, 0.08, 0.09, 0.10), nrow = 5),
    lower = matrix(c(0.1, 0.1, 0.2, 0.2, 0.3, 0.3, 0.4, 0.4, 0.5, 0.5), nrow = 5),
    upper = matrix(c(0.9, 0.9, 0.8, 0.8, 0.7, 0.7, 0.6, 0.6, 0.5, 0.5), nrow = 5),
    strata = c(3L, 2L),
    states = c("cens", "event")
  ), class = c("survfitms", "survfit"))
}

case_g <- function() {
  structure(list(
    n = 4L,
    time = c(1, 2, 5),
    n.risk = matrix(c(4, 3, 2, 3, 2, 1), nrow = 3),
    n.event = matrix(c(1, 0, 1, 0, 1, 0), nrow = 3),
    pstate = array(c(0.7, 0.6, 0.5, 0.3, 0.4, 0.5), dim = c(3, 1, 2)),
    p0 = matrix(c(0.7, 0.3), nrow = 1),
    sp0 = matrix(c(0.02, 0.03), nrow = 1),
    cumhaz = matrix(c(0.3, 0.4, 0.5, 0.6, 0.7, 0.8), nrow = 3),
    std.err = matrix(c(0.1, 0.2, 0.3, 0.1, 0.2, 0.3), nrow = 3),
    lower = matrix(c(0.2, 0.3, 0.4, 0.1, 0.2, 0.3), nrow = 3),
    upper = matrix(c(0.8, 0.7, 0.6, 0.9, 0.8, 0.7), nrow = 3),
    states = c("cens", "event")
  ), class = c("survfitms", "survfit"))
}

case_h <- function() {
  structure(list(
    n = 3L,
    time = c(0, 2, 3),
    n.risk = c(3, 2, 1),
    n.event = c(0, 1, 1),
    n.censor = c(0, 0, 0),
    surv = c(1, 0.5, 0.25),
    std.err = c(0, 0.2, 0.3),
    cumhaz = c(0, 0.6931, 1.3863),
    logse = TRUE,
    type = "right"
  ), class = "survfit")
}

case_i <- function() {
  structure(list(
    n = 3L,
    time = c(1, 2),
    n.risk = c(3, 2),
    n.event = c(1, 1),
    n.censor = c(0, 0),
    surv = c(0.66, 0.33),
    time0 = TRUE,
    type = "right"
  ), class = "survfit")
}

case_j <- function() {
  x <- case_a()
  class(x) <- c("survfit0", "survfit")
  x
}

serialize_fit <- function(label, obj) {
  out <- c(label, paste("class", paste(class(obj), collapse = "|")))
  nms <- sort(names(obj), method = "radix")
  for (k in nms) {
    v <- obj[[k]]
    if (is.null(v) || is.character(v) || is.list(v)) next
    out <- c(out, paste(k, paste(sprintf("%.17g", as.numeric(v)), collapse = " ")))
  }
  out
}

one <- function() {
  cases <- list(
    A = case_a(), B = case_b(), C = case_c(), D = case_d(), E = case_e(),
    F = case_f(), G = case_g(), H = case_h(), I = case_i(), J = case_j()
  )
  out <- character(0)
  for (nm in names(cases)) {
    res <- survival::survfit0(cases[[nm]])
    out <- c(out, serialize_fit(paste("case", nm), res))
  }
  out
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste(value, collapse = "\n"), "\n", sep = "")
cat("MS\n")
cat(sprintf("%.17g\n", median(elapsed) * 1000))
