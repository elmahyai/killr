.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages({
  library(nlme)
  library(jsonlite)
})
if (packageDescription("nlme")$Version != "3.1-171") {
  stop("expected nlme 3.1-171")
}

# Captures the condensed linear model (conLin) that lme() passes to
# Initialize.reStruct for the Pixel help example, and writes it as a fixed
# input for the Python proofs. Run from the repository root:
#   Rscript packages/nlme/proof/reStruct-conlin-capture-r.R
data(Pixel)
captured <- NULL
trace("Initialize.reStruct",
      tracer = quote(assign("captured", conLin, envir = globalenv())),
      where = asNamespace("nlme"), print = FALSE)
fit <- lme(pixel ~ day + day^2, data = Pixel, random = list(Dog = ~day, Side = ~1))
untrace("Initialize.reStruct", where = asNamespace("nlme"))

out <- list(
  N = nrow(captured$Xy),
  ncol = ncol(captured$Xy),
  colnames = colnames(captured$Xy),
  Xy = as.vector(captured$Xy),
  sigma = captured$sigma,
  dims = captured$dims
)
target <- file.path("packages", "nlme", "proof", "data", "reStruct-pixel-conlin.json")
write_json(out, target, auto_unbox = TRUE, digits = NA, pretty = FALSE)
cat("wrote", target, "\n")
