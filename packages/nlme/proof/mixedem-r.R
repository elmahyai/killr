.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

# Bit-exact proof of nlme's mixed_EM (nlmefit.c), the EM start used by lme().
# Each case fits an lme model in R and captures the inputs of the first
# .C("mixed_EM") call that MEEM() makes (R/lme.R). The captured inputs are
# replayed through the native entry point, which is timed; the Python proof
# (mixedem-py.py) reads these inputs and compares its nlme_mixedem.mixed_em
# outputs with these R outputs.

ns <- asNamespace("nlme")
orig_MEEM <- get("MEEM", ns)
captured <- NULL
wrapper <- function(object, conLin, niter = 0) {
  if (niter > 0 && is.null(captured)) {
    dd <- conLin$dims
    pdCl <- attr(object, "settings")[-(1:3)]
    pdCl[pdCl == -1] <- 0
    precvec <- unlist(pdFactor(object))
    captured <<- list(
      Xy = as.double(conLin$Xy),
      dims = as.integer(unlist(dd)),
      precvec = as.double(precvec),
      niter = as.integer(niter),
      pdCl = as.integer(pdCl),
      RML = as.integer(attr(object, "settings")[1L]),
      sigma = as.double(conLin$sigma)
    )
  }
  orig_MEEM(object, conLin, niter)
}
unlockBinding("MEEM", ns)
assign("MEEM", wrapper, envir = ns)

replay <- function(inp) {
  .C(get("mixed_EM", ns),
    inp$Xy, inp$dims, precvec = inp$precvec, inp$niter, inp$pdCl, inp$RML,
    double(1), double(length(inp$precvec)), double(1), inp$sigma)
}

num <- function(x) paste0("[", paste(sprintf("%.17g", x), collapse = ","), "]")
ints <- function(x) paste0("[", paste(as.integer(x), collapse = ","), "]")

fits <- list(
  "orthodont-pdSymm-REML" = quote(lme(distance ~ age, data = Orthodont)),
  "orthodont-pdSymm-ML" = quote(lme(distance ~ age, data = Orthodont, method = "ML")),
  "orthodont-pdDiag-REML" = quote(lme(distance ~ age, data = Orthodont, random = list(Subject = pdDiag(~age)))),
  "orthodont-pdIdent-REML" = quote(lme(distance ~ age, data = Orthodont, random = list(Subject = pdIdent(~age)))),
  "orthodont-pdCompSymm-REML" = quote(lme(distance ~ age, data = Orthodont, random = list(Subject = pdCompSymm(~age)))),
  "pixel-nested-pdSymm-REML" = quote(lme(pixel ~ day + I(day^2), data = Pixel, random = list(Dog = ~day, Side = ~1)))
)

pieces <- character()
for (name in names(fits)) {
  captured <- NULL
  invisible(eval(fits[[name]]))
  if (is.null(captured)) stop("no mixed_EM call captured for ", name)
  c0 <- captured
  out <- replay(c0)
  replay(c0)
  times <- numeric(20)
  for (i in seq_len(20)) {
    t0 <- as.numeric(Sys.time())
    replay(c0)
    times[[i]] <- as.numeric(Sys.time()) - t0
  }
  pieces <- c(pieces, sprintf(
    paste0(
      "{\"name\":\"%s\",\"Xy\":%s,\"dims\":%s,\"precvec\":%s,\"niter\":%d,\"pdCl\":%s,\"RML\":%d,\"sigma\":%s,",
      "\"out\":{\"precvec\":%s,\"logLik\":%s,\"Ra\":%s,\"lRSS\":%s},\"median_ms\":%.17g}"
    ),
    name, num(c0$Xy), ints(c0$dims), num(c0$precvec), c0$niter, ints(c0$pdCl), c0$RML, num(c0$sigma),
    num(out[["precvec"]]), num(out[[7]]), num(out[[8]]), num(out[[9]]),
    median(times) * 1000
  ))
}
assign("MEEM", orig_MEEM, envir = ns)
cat(sprintf("{\"cases\":[%s]}\n", paste(pieces, collapse = ",")))
