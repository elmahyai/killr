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
  rs <- reStruct(list(Dog = ~day, Side = ~1), data = Pixel)
  rs1 <- Initialize(rs, Pixel, conLin = captured_conlin)
  rs2 <- Initialize(rs1, Pixel, conLin = captured_conlin)
  c(logDet(rs1), logDet(rs2))
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
