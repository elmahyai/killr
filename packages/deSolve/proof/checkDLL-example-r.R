.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(deSolve))
if (packageDescription("deSolve")$Version != "1.42") stop("expected deSolve 1.42")

sym <- checkDLL(
  func = "aquaphy", jacfunc = NULL, dllname = "deSolve",
  initfunc = "iniaqua", verbose = TRUE, nout = 6,
  outnames = c(
    "PAR", "TotalN", "PhotoSynthesis",
    "NCratio", "ChlCratio", "Chlorophyll"
  ),
  JT = 1
)

kind <- function(x) {
  if (is.null(x)) return("NULL")
  if (is.logical(x) && length(x) == 1L && is.na(x)) return("NA")
  if (inherits(x, "NativeSymbol")) return("NativeSymbol")
  paste(class(x), collapse = ",")
}

cat("class: deSolve.symbols\n")
cat("ModelInit:", kind(sym$ModelInit), "\n")
cat("Func:", kind(sym$Func), "\n")
cat("JacFunc:", kind(sym$JacFunc), "\n")
cat("Nglobal:", sym$Nglobal, "\n")
cat("colnames:", paste(sym$Nmtot$colnames, collapse = " "), "\n")
