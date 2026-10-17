.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(nlme))
stopifnot(isTRUE(packageVersion("nlme") == "3.1-171"))

script_dir <- function() {
  args <- commandArgs(trailingOnly = FALSE)
  file_arg <- grep("^--file=", args, value = TRUE)
  dirname(normalizePath(sub("^--file=", "", file_arg[[1]])))
}

names_fp <- function(x) {
  x <- as.character(x)
  out <- length(x)
  for (s in x) {
    codes <- utf8ToInt(s)
    out <- c(out, nchar(s), sum(codes * seq_along(codes)))
  }
  as.numeric(out)
}

here <- script_dir()
data_dir <- file.path(here, "data")
dir.create(data_dir, recursive = TRUE, showWarnings = FALSE)
write.csv(
  data.frame(Seed = as.character(Loblolly$Seed), age = Loblolly$age,
             height = Loblolly$height),
  file.path(data_dir, "nlsList-loblolly.csv"), row.names = FALSE
)
writeLines(levels(Loblolly$Seed), file.path(data_dir, "nlsList-levels.txt"))

build <- function() {
  nlsList(height ~ SSasympOff(age, Asym, lrc, c0) | Seed, data = Loblolly,
          start = c(Asym = 100, lrc = -1.5, c0 = 0))
}

one <- function() {
  fit <- build()
  cf <- as.matrix(coef(fit))
  c(as.numeric(cf), names_fp(rownames(cf)), names_fp(colnames(cf)))
}

example <- function() {
  fit <- build()
  cf <- as.matrix(coef(fit))
  lines <- c(
    sprintf("groups: %d", nrow(cf)),
    sprintf("coefficients: %s", paste(colnames(cf), collapse = " "))
  )
  for (i in seq_len(nrow(cf))) {
    lines <- c(lines, sprintf("%s: %s", rownames(cf)[i],
                              paste(sprintf("%.10g", cf[i, ]), collapse = " ")))
  }
  lines
}

out_dir <- file.path(here, "..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
writeLines(example(), file.path(out_dir, "nlsList-r.txt"))

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
