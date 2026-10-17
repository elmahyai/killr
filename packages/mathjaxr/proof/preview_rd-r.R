script <- sub("^--file=", "", grep("^--file=", commandArgs(), value = TRUE))
root <- normalizePath(file.path(dirname(script), ".."), mustWork = TRUE)
outdir <- file.path(root, "docs", "output")
dir.create(outdir, recursive = TRUE, showWarnings = FALSE)
fixture <- file.path(tempdir(), "mathjaxr-preview")
dir.create(file.path(fixture, "man"), recursive = TRUE, showWarnings = FALSE)
writeLines(c("\\name{demo}", "\\title{Demo}", "\\description{Hello world.}"),
           file.path(fixture, "man", "demo.Rd"))
writeLines(c("Package: demo", "Version: 1.0"), file.path(fixture, "DESCRIPTION"))
setwd(fixture)
mathjaxr::preview_rd("demo.Rd", view = FALSE, type = "txt")
generated <- file.path(tempdir(), "demo.Rd.txt")
file.copy(generated, file.path(outdir, "preview_rd-r.txt"), overwrite = TRUE)

times <- numeric(20)
for (i in seq_along(times)) {
  started <- Sys.time()
  mathjaxr::preview_rd("demo.Rd", view = FALSE, type = "txt")
  times[[i]] <- as.numeric(difftime(Sys.time(), started, units = "secs")) * 1000
}
cat(sprintf("r_ms=%.6f\n", median(times)))
cat(sprintf("output=%s\n", file.path(outdir, "preview_rd-r.txt")))
