suppressPackageStartupMessages(library(generics))
stopifnot(identical(as.character(packageVersion("generics")), "0.1.4"))

encode <- function(x) {
  if (is.logical(x)) {
    return(paste(ifelse(is.na(x), "NA", ifelse(x, "TRUE", "FALSE")), collapse = ","))
  }
  if (is.numeric(x)) {
    return(paste(vapply(x, function(v) {
      if (is.na(v)) {
        if (is.nan(v)) "NaN" else "NA"
      } else sprintf("%.17g", v)
    }, ""), collapse = ","))
  }
  paste(as.character(x), collapse = ",")
}

one <- function() {
  a <- c(3, NA_real_, NaN, 3, 1, NA_real_)
  b <- c(2, NA_real_, NaN, 2)
  c(
    paste0("is.element=", encode(generics::is.element(a, b))),
    paste0("setdiff=", encode(generics::setdiff(a, b))),
    paste0("setequal=", encode(generics::setequal(a, b))),
    paste0("union=", encode(generics::union(a, b))),
    paste0("empty=", encode(generics::union(numeric(), numeric()))),
    paste0("chars=", encode(generics::union(c("b", "a", "b"), c("a", "c")))),
    paste0("logical=", encode(generics::is.element(c(TRUE, FALSE), c(FALSE))))
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat("VALUE\n", paste(value, collapse = "\n"), "\n", sep = "")
cat(sprintf("MS %.17g\n", median(elapsed) * 1000))

cmd <- commandArgs(trailingOnly = FALSE)
file_arg <- cmd[grep("^--file=", cmd)]
script <- if (length(file_arg)) {
  normalizePath(sub("^--file=", "", file_arg[[1]]))
} else {
  file.path(getwd(), "packages", "generics", "proof", "set_helpers-r.R")
}
out_dir <- file.path(normalizePath(file.path(dirname(script), "..")), "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
writeLines(value, file.path(out_dir, "set_helpers-r.txt"))
