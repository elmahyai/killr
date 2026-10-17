.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
if (packageDescription("nlme")$Version != "3.1-171") {
  stop("expected nlme 3.1-171")
}
# pdCompSymm is on the 2x2 Dog block only: R cannot initialize a 1x1 pdCompSymm block (Side ~1).
# Same inputs as pdCompSymm-coverage-py.py: the Pixel model, with the conLin that lme()
# passes to Initialize.reStruct captured before timing (as in reStruct-conlin-capture-r.R).
data(Pixel)
captured_conlin <- NULL
trace("Initialize.reStruct",
      tracer = quote(assign("captured_conlin", conLin, envir = globalenv())),
      where = asNamespace("nlme"), print = FALSE)
invisible(lme(pixel ~ day + day^2, data = Pixel, random = list(Dog = ~day, Side = ~1)))
untrace("Initialize.reStruct", where = asNamespace("nlme"))

timed <- function(f) {
  value <- as.numeric(f())
  elapsed <- numeric(20)
  for (i in seq_len(20)) {
    t0 <- as.numeric(Sys.time())
    f()
    elapsed[[i]] <- as.numeric(Sys.time()) - t0
  }
  list(value = value, median_ms = median(elapsed) * 1000)
}
emit <- function(res) {
  parts <- vapply(names(res), function(n) {
    sprintf("\"%s\":{\"value\":[%s],\"median_ms\":%.17g}", n,
            paste(sprintf("%.17g", res[[n]]$value), collapse = ","),
            res[[n]]$median_ms)
  }, "")
  cat("{", paste(parts, collapse = ","), "}\n", sep = "")
}

make_rs <- function() {
  Initialize(reStruct(list(Dog = pdCompSymm(~day), Side = ~1), data = Pixel),
             Pixel, conLin = captured_conlin)
}
# Already-initialized blocks: no Initialize.reStruct, so no EM step (the nlmemixed
# kernel refuses compound-symmetry EM). Dog is 2x2 compound symmetry; Side is 1x1 logChol.
make_init_rs <- function() {
  dog <- pdCompSymm(matrix(c(2, 0.6, 0.6, 2), 2), form = ~day, data = Pixel)
  side <- pdLogChol(matrix(4), form = ~1, data = Pixel)
  reStruct(list(Dog = dog, Side = side), data = Pixel)
}

fingerprint <- function(object) {
  c(
    as.vector(attr(object, "settings")),
    as.vector(attr(object, "plen")),
    unlist(lapply(object, function(el) as.vector(coef(el)))),
    unlist(lapply(object, function(el) as.vector(pdMatrix(el))))
  )
}
init_fn <- function() fingerprint(make_rs())
logdet_fn <- function() c(logDet(make_init_rs()[[1]]), logDet(make_init_rs()))
recalc_fn <- function() {
  con <- captured_conlin
  con$logLik <- 0.5
  r <- recalc(make_init_rs(), con)
  c(as.vector(r$Xy), as.numeric(r$logLik))
}

emit(list(
  Initialize = timed(init_fn),
  logDet = timed(logdet_fn),
  recalc = timed(recalc_fn)
))
