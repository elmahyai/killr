.libPaths(c("/tmp/permute-lib", .libPaths()))
library(permute)

out <- file.path(dirname(sub("^--file=", "", commandArgs()[grep("^--file=", commandArgs())])),
                 "..", "docs", "output")
dir.create(out, recursive = TRUE, showWarnings = FALSE)

ctrl <- how(within = Within(type = "free"), nperm = 5, observed = TRUE)
mat <- allPerms(4, ctrl)
calls <- list(
  getRow = function() getRow(ctrl),
  getCol = function() getCol(ctrl),
  getDim = function() getDim(ctrl),
  getNperm = function() getNperm(ctrl),
  getMaxperm = function() getMaxperm(ctrl),
  getMinperm = function() getMinperm(ctrl),
  getComplete = function() getComplete(ctrl),
  getMake = function() getMake(ctrl),
  getObserved = function() getObserved(ctrl),
  getAllperms = function() getAllperms(ctrl),
  getControl = function() getControl(mat)
)

canonical <- function(x) {
  if (is.null(x)) return("None")
  if (is.atomic(x)) {
    if (!length(x)) return("[]")
    return(paste(vapply(x, function(v) {
      if (is.na(v)) "NA" else if (is.logical(v)) tolower(as.character(v)) else as.character(v)
    }, character(1)), collapse = ","))
  }
  if (is.list(x)) {
    y <- unclass(x)
    keep <- intersect(names(y), c("type", "constant", "mirror", "ncol", "nrow",
                                  "strata", "within", "plots", "blocks", "nperm",
                                  "complete", "maxperm", "minperm", "all.perms",
                                  "make", "observed"))
    return(paste(paste0(keep, "=", vapply(y[keep], canonical, character(1))),
                 collapse = ";"))
  }
  as.character(x)
}

values <- file.path(out, "getters-r-values.txt")
writeLines(vapply(names(calls), function(nm) paste(nm, canonical(calls[[nm]]()), sep = "\t"),
                  character(1)), values)

timing <- vapply(calls, function(f) {
  f()
  median(replicate(20, system.time(replicate(1000, f()))[["elapsed"]] * 1000 / 1000))
}, numeric(1))
writeLines(c("name\tr_ms", paste(names(timing), format(timing, scientific = FALSE,
                                                       digits = 12), sep = "\t")),
           file.path(out, "getters-r-timing.tsv"))
