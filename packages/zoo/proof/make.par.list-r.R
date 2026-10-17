.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(zoo))
stopifnot(packageVersion("zoo") == "1.9-1")

fmt_val <- function(v) {
  if (is.null(v)) return("null")
  if (is.character(v)) return(paste(ifelse(is.na(v), "NA", v), collapse = "|"))
  if (length(v) == 0) return("")
  paste(vapply(as.numeric(v), function(z) {
    if (is.na(z)) "NA" else if (is.infinite(z)) { if (z > 0) "Inf" else "-Inf" } else sprintf("%.16g", z)
  }, ""), collapse = "|")
}

fmt_par <- function(y) {
  nms <- names(y)
  if (is.null(nms)) nms <- rep("", length(y))
  paste(vapply(seq_along(y), function(i) paste0(nms[[i]], ": ", fmt_val(y[[i]])), ""), collapse = "\n")
}

one <- function() {
  nams <- c("A", "B", "C")
  parts <- c(
    paste0("CASE named-unnamed\n", fmt_par(make.par.list(nams, list(A = c(1, 2), c(3, 4)), 5, 3, 1))),
    paste0("CASE named-only\n", fmt_par(make.par.list(nams, list(B = 2), 5, 3, 1))),
    paste0("CASE atomic-multi\n", fmt_par(make.par.list(nams, c(1, 2, 3), 4, 3, 9))),
    paste0("CASE atomic-single\n", fmt_par(make.par.list("A", c(1, 2, 3), 5, 1, 9))),
    paste0("CASE scalar-multi\n", fmt_par(make.par.list(nams, 7, 4, 3, 9))),
    paste0("CASE mixed-list\n", fmt_par(make.par.list(nams, list(C = 4, 2), 3, 3, 1))),
    paste0("CASE pch-partial\n", fmt_par(make.par.list(nams, list(A = 1:5, B = 3), 5, 3, par("pch")))),
    paste0("CASE recycle-false-unnamed\n", fmt_par(make.par.list(nams, list(A = 8, 3, 4), 2, 3, 0, recycle = FALSE))),
    paste0("CASE def-vector\n", fmt_par(suppressWarnings(make.par.list(nams, list(A = 5), 3, 3, c(1, 2), recycle = FALSE)))),
    paste0("CASE empty-numeric\n", fmt_par(make.par.list(c("A", "B"), list(A = numeric(0), 5), 3, 2, 1))),
    paste0("CASE null-def\n", fmt_par(suppressWarnings(make.par.list(nams, list(A = c(0, 1)), 2, 3, NULL))))
  )
  err <- tryCatch(
    make.par.list(nams, list(A = 1, B = 2), 2, 3, 0, recycle = TRUE),
    error = function(e) conditionMessage(e)
  )
  parts <- c(parts, paste0("CASE error-recycle\nERROR ", err))
  paste(parts, collapse = "\n\n")
}

value <- one()
out <- "/home/ahmed/killr_projects/killr/packages/zoo/docs/output/make.par.list-r.txt"
dir.create(dirname(out), recursive = TRUE, showWarnings = FALSE)
writeLines(value, out)
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf("{\"median_ms\":%.17g}\n", median(elapsed) * 1000))
