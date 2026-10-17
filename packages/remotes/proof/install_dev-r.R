.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(remotes))
stopifnot(packageVersion("remotes") == "2.5.0")

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- normalizePath(sub("^--file=", "", file_arg[[1]]))
out_dir <- file.path(dirname(script), "..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

cran <- tempfile("fakecran")
desc_dir <- file.path(cran, "web", "packages", "minipkg")
dir.create(desc_dir, recursive = TRUE)
writeLines(c(
  "Package: minipkg",
  "Version: 0.0.1",
  "URL: https://bitbucket.org/djnavarro/lsr"
), file.path(desc_dir, "DESCRIPTION"))
cran_url <- paste0("file://", normalizePath(cran))
lib <- tempfile("lib")
dir.create(lib)
installed <- tryCatch(
  install_dev("minipkg", cran_url = cran_url, dependencies = FALSE, upgrade = "never", quiet = TRUE, build = FALSE, lib = lib),
  error = function(e) "error"
)

one <- function() {
  refs <- remotes:::dev_split_ref("minipkg")
  desc <- read.dcf(file.path(cran, "web", "packages", refs[["pkg"]], "DESCRIPTION"))
  c(refs[["pkg"]], unname(desc[, "URL"]))
}
value <- one()
stopifnot(identical(value, c("minipkg", "https://bitbucket.org/djnavarro/lsr")))

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  got <- one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
  stopifnot(identical(got, value))
}

sentence <- "install_dev() would install lsr from https://bitbucket.org/djnavarro/lsr."
writeLines(sentence, file.path(out_dir, "install_dev-r.txt"))
installed_json <- if (identical(installed, "lsr")) "\"lsr\"" else "\"error\""
cat(sprintf("{\"package\":\"minipkg\",\"url\":\"https://bitbucket.org/djnavarro/lsr\",\"installed\":%s,\"median_ms\":%.17g}\n", installed_json, median(elapsed) * 1000))
