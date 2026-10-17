if (!interactive() && Sys.getenv("CODA_TTY") != "1") {
  file_arg <- grep("^--file=", commandArgs(trailingOnly = FALSE), value = TRUE)
  if (length(file_arg) == 1L) {
    script <- sub("^--file=", "", file_arg[[1L]])
    Sys.setenv(CODA_TTY = "1")
    status <- system2(
      "script",
      c("-q", "-c", shQuote("R --vanilla --quiet --no-echo"), "/dev/null"),
      stdin = script,
      stdout = FALSE,
      stderr = FALSE
    )
    quit(status = status)
  }
}

.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(coda))
if (as.character(packageVersion("coda")) != "0.19.4.1") stop("expected coda 0.19-4.1")
options(warn = -1)

root <- normalizePath(".", winslash = "/", mustWork = FALSE)
out_dir <- file.path(root, "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

one <- function() {
  read.and.check("Enter a probability", lower = 0, upper = 1, default = 0.5)
}

sink(file.path(out_dir, "read.and.check-r.txt"))
value <- one()
0.25
sink()
elapsed <- numeric(20)
sink("/dev/null")
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
0.25
0.25
0.25
0.25
0.25
0.25
0.25
0.25
0.25
0.25
0.25
0.25
0.25
0.25
0.25
0.25
0.25
0.25
0.25
0.25

sink()
parts <- sprintf("%.17g", value)
out <- sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(parts, collapse = ","),
  median(elapsed) * 1000
)
writeLines(out, con = file.path(root, "proof", "read.and.check-r.txt"))
q(save = "no")
