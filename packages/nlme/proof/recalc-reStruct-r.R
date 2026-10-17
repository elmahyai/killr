.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
if (packageDescription("nlme")$Version != "3.1-171") {
  stop("expected nlme 3.1-171")
}
data(Pixel)
# Fixed input: the conLin that lme() passes to Initialize.reStruct on the Pixel
# help example (the same capture as reStruct-conlin-capture-r.R), taken before timing.
captured_conlin <- NULL
trace("Initialize.reStruct",
      tracer = quote(assign("captured_conlin", conLin, envir = globalenv())),
      where = asNamespace("nlme"), print = FALSE)
invisible(lme(pixel ~ day + day^2, data = Pixel, random = list(Dog = ~day, Side = ~1)))
untrace("Initialize.reStruct", where = asNamespace("nlme"))
one <- function() {
  con1 <- captured_conlin
  con1$logLik <- 0.5
  rs1 <- Initialize(reStruct(list(Dog = ~day, Side = ~1), data = Pixel), Pixel, conLin = captured_conlin)
  r1 <- recalc(rs1, con1)
  con2 <- captured_conlin
  con2$logLik <- 0.5
  con2$sigma <- 1.5
  rsR <- Initialize(reStruct(list(Dog = ~day, Side = ~1), data = Pixel, REML = TRUE), Pixel, conLin = con2)
  r2 <- recalc(rsR, con2)
  c(as.numeric(r1$logLik), as.numeric(r2$logLik))
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(sprintf("%.17g", value), collapse = ","),
  median(elapsed) * 1000
))
