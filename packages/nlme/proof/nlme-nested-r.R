.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
if (packageDescription("nlme")$Version != "3.1-171") {
  stop("expected nlme 3.1-171")
}

# Write the Pixel rows that the Python side reads (outside the timed calls).
script_dir <- function() {
  args <- commandArgs(trailingOnly = FALSE)
  file_arg <- grep("^--file=", args, value = TRUE)
  dirname(normalizePath(sub("^--file=", "", file_arg[[1]])))
}
data_dir <- file.path(script_dir(), "data")
dir.create(data_dir, recursive = TRUE, showWarnings = FALSE)
data(Pixel)
write.csv(
  data.frame(Dog = as.character(Pixel$Dog), Side = as.character(Pixel$Side),
             day = Pixel$day, pixel = Pixel$pixel),
  file.path(data_dir, "nlme-pixel.csv"), row.names = FALSE
)

# Structure 2: nested two-level random structure. Random intercept on Asym for
# Dog, and for Side within Dog (Dog/Side), both pdLogChol by default.
one <- function() {
  fm <- nlme(
    pixel ~ SSasymp(day, Asym, R0, lrc),
    data = Pixel,
    fixed = Asym + R0 + lrc ~ 1,
    random = list(Dog = Asym ~ 1, Side = Asym ~ 1),
    start = c(Asym = 1090, R0 = 1040, lrc = -2)
  )
  # The stored pdMat is the random covariance divided by sigma^2.
  v <- lapply(pdMatrix(fm$modelStruct$reStruct), function(m) fm$sigma^2 * m)
  c(fixef(fm), v$Dog[1, 1], v$Side[1, 1], fm$sigma,
    as.numeric(logLik(fm)), fm$numIter)
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
