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

choices <- c("alpha", "beta", "gamma", "delta", "epsilon")
one <- function() {
  multi.menu(choices, "Pick variables", c("Id", "Name"))
}

sink(file.path(out_dir, "multi.menu-r.txt"))
value <- one()
1,3:5
sink()
elapsed <- numeric(20)
sink("/dev/null")
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
1,3:5
1,3:5
1,3:5
1,3:5
1,3:5
1,3:5
1,3:5
1,3:5
1,3:5
1,3:5
1,3:5
1,3:5
1,3:5
1,3:5
1,3:5
1,3:5
1,3:5
1,3:5
1,3:5
1,3:5

sink()
parts <- sprintf("%.17g", value)
out <- sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(parts, collapse = ","),
  median(elapsed) * 1000
)
writeLines(out, con = file.path(root, "proof", "multi.menu-r.txt"))
q(save = "no")
