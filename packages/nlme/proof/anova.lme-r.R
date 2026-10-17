.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))

one <- function() {
  fm <- lme(distance ~ age, data = Orthodont, control = lmeControl(apVar = FALSE))
  av <- anova(fm)
  c(av$numDF, av$denDF, av[["F-value"]], av[["p-value"]])
}

NLMINB_LOG <- list()
record_nlminb <- function(rv) {
  NLMINB_LOG[[length(NLMINB_LOG) + 1L]] <<- c(rv$iterations, rv$evaluations)
}
ns <- asNamespace("nlme")
invisible(trace("nlminb", where = ns, print = FALSE, exit = quote(record_nlminb(returnValue()))))
value <- one()
invisible(untrace("nlminb", where = ns))
iterations <- paste0("[", paste(vapply(NLMINB_LOG, function(v) paste0("[", paste(as.integer(v), collapse = ","), "]"), ""), collapse = ","), "]")
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"value\":[%s],\"iterations\":%s,\"median_ms\":%.17g}\n",
  paste(sprintf("%.17g", value), collapse = ","),
  iterations,
  median(elapsed) * 1000
))
