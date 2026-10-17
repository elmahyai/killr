.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
if (packageDescription("nlme")$Version != "3.1-171") {
  stop("expected nlme 3.1-171")
}

# Pixel model: the conLin that lme() passes to Initialize.reStruct, captured before timing
# (the same capture as pdSymm-coverage-r.R). The pd classes are recalculated with it.
data(Pixel)
captured_conlin <- NULL
invisible(trace("Initialize.reStruct",
      tracer = quote(assign("captured_conlin", conLin, envir = globalenv())),
      where = asNamespace("nlme"), print = FALSE))
invisible(lme(pixel ~ day + day^2, data = Pixel, random = list(Dog = ~day, Side = ~1)))
invisible(untrace("Initialize.reStruct", where = asNamespace("nlme")))
pixel_con <- captured_conlin
pixel_con$logLik <- 0.5

con <- list(Xy = matrix(as.double(1:14), 7, 2), logLik = 0.5)
dat_sub <- data.frame(
  Subject = c("a", "a", "a", "a", "b", "b", "b"),
  t = c(1, 2, 3, 4, 1, 2, 4)
)
dat_ar <- data.frame(
  Subject = c("a", "a", "a", "b", "b", "b", "b"),
  t = c(1, 2, 4, 1, 2, 3, 5)
)
dat_xy <- data.frame(
  Subject = c("a", "a", "a", "a", "b", "b", "b"),
  x = c(0, 1, 0.5, 2, 0.2, 1.4, 2.6),
  y = c(0, 0, 1, 0.5, 0.3, 1.1, 0.4)
)

pair <- function(object, conLin) list(object = object, conLin = conLin)

pixel_rs <- function(pdClass) {
  Initialize(reStruct(list(Dog = ~day, Side = ~1), pdClass = pdClass, data = Pixel),
             Pixel, conLin = captured_conlin)
}

# Already-initialized pdCompSymm block (no EM step), as in pdCompSymm-coverage-r.R.
pdcomp_rs <- function() {
  dog <- pdCompSymm(matrix(c(2, 0.6, 0.6, 2), 2), form = ~day, data = Pixel)
  side <- pdLogChol(matrix(4), form = ~1, data = Pixel)
  reStruct(list(Dog = dog, Side = side), data = Pixel)
}

# One setup per class: the recalc inputs are built here, outside the timer.
cases <- list(
  corSymm = function() list(
    pair(Initialize(corSymm(c(0.3, 0.1, 0.2, 0.05, 0.1, 0.25), form = ~ t | Subject), dat_sub), con),
    pair(Initialize(corSymm(form = ~ t | Subject), dat_sub), con)
  ),
  corAR1 = function() list(
    pair(Initialize(corAR1(0.3, form = ~ t | Subject), dat_ar), con),
    pair(Initialize(corAR1(-0.4, form = ~ t | Subject), dat_ar), con)
  ),
  pdSymm = function() list(pair(pixel_rs("pdSymm"), pixel_con)),
  pdDiag = function() list(pair(pixel_rs("pdDiag"), pixel_con)),
  pdIdent = function() list(pair(pixel_rs("pdIdent"), pixel_con)),
  pdCompSymm = function() list(pair(pdcomp_rs(), pixel_con)),
  corLin = function() list(
    pair(Initialize(corLin(3, form = ~ x + y | Subject), dat_xy), con),
    pair(Initialize(corLin(c(3, 0.2), form = ~ x + y | Subject, nugget = TRUE, metric = "man"), dat_xy), con)
  ),
  corRatio = function() list(
    pair(Initialize(corRatio(3, form = ~ x + y | Subject), dat_xy), con),
    pair(Initialize(corRatio(c(3, 0.2), form = ~ x + y | Subject, nugget = TRUE, metric = "man"), dat_xy), con)
  ),
  corSpher = function() list(
    pair(Initialize(corSpher(3, form = ~ x + y | Subject), dat_xy), con),
    pair(Initialize(corSpher(c(3, 0.2), form = ~ x + y | Subject, nugget = TRUE, metric = "man"), dat_xy), con)
  ),
  corExp = function() list(
    pair(Initialize(corExp(3, form = ~ x + y | Subject), dat_xy), con),
    pair(Initialize(corExp(c(3, 0.2), form = ~ x + y | Subject, nugget = TRUE, metric = "man"), dat_xy), con)
  ),
  corGaus = function() list(
    pair(Initialize(corGaus(3, form = ~ x + y | Subject), dat_xy), con),
    pair(Initialize(corGaus(c(3, 0.2), form = ~ x + y | Subject, nugget = TRUE, metric = "man"), dat_xy), con)
  ),
  corSpatial = function() list(
    pair(Initialize(corSpatial(3, form = ~ x + y | Subject, type = "spherical"), dat_xy), con),
    pair(Initialize(corSpatial(c(3, 0.2), form = ~ x + y | Subject, nugget = TRUE,
                               type = "exponential", metric = "man"), dat_xy), con)
  ),
  corCAR1 = function() list(
    pair(Initialize(corCAR1(0.2, form = ~ t | Subject), dat_sub), con),
    pair(Initialize(corCAR1(0.7, form = ~ t | Subject), dat_sub), con)
  )
)

# Column-major Xy followed by logLik, for each pair in order.
run_pairs <- function(pairs) {
  unlist(lapply(pairs, function(p) {
    r <- recalc(p$object, p$conLin)
    c(as.vector(r$Xy), as.numeric(r$logLik))
  }))
}

parts <- character(0)
for (name in names(cases)) {
  pairs <- cases[[name]]()
  value <- run_pairs(pairs)
  elapsed <- numeric(20)
  for (i in seq_len(20)) {
    t0 <- as.numeric(Sys.time())
    run_pairs(pairs)
    elapsed[[i]] <- as.numeric(Sys.time()) - t0
  }
  parts <- c(parts, sprintf(
    "\"%s\":{\"value\":[%s],\"median_ms\":%.17g}",
    name,
    paste(sprintf("%.17g", value), collapse = ","),
    median(elapsed) * 1000
  ))
}
cat("{", paste(parts, collapse = ","), "}\n", sep = "")
