.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(coda))
if (as.character(packageVersion("coda")) != "0.19.4.1") stop("expected coda 0.19-4.1")
options(warn = -1)

root <- normalizePath(".", winslash = "/", mustWork = FALSE)
out_dir <- file.path(root, "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

digest_lines <- function(lines) {
  sum(vapply(lines, function(line) sum(utf8ToInt(line)), numeric(1)))
}

one <- function() {
  coda.options(default = TRUE)
  coda.options(frac1 = 0.12, digits = 4)
  captured <- capture.output(display.coda.options(stats = TRUE, diags = TRUE, plots = FALSE))
  c(
    digest_lines(captured),
    coda.options("frac1"),
    coda.options("digits"),
    as.numeric(coda.options("combine.stats")),
    length(captured)
  )
}

sink(file.path(out_dir, "display.coda.options-r.txt"))
one()
sink()

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
parts <- sprintf("%.17g", value)
writeLines(
  sprintf(
    "{\"value\":[%s],\"median_ms\":%.17g}\n",
    paste(parts, collapse = ","),
    median(elapsed) * 1000
  ),
  con = file.path(root, "display.coda.options-r.txt")
)
