.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(remotes))
stopifnot(packageVersion("remotes") == "2.5.0")

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- normalizePath(sub("^--file=", "", file_arg[[1]]))
out_dir <- file.path(dirname(script), "..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

repos <- "https://cloud.r-project.org"
type <- "source"

path <- download_version("remotes", "2.5.0", repos = repos, type = type)
magic <- readBin(path, "raw", n = 2L)
stopifnot(identical(magic, as.raw(c(0x1f, 0x8b))))
files <- untar(path, list = TRUE)
desc <- files[grepl("DESCRIPTION$", files)]
stopifnot(length(desc) >= 1L)
ex <- tempfile()
dir.create(ex)
untar(path, files = desc[[1]], exdir = ex)
dcf <- read.dcf(file.path(ex, desc[[1]]))
base <- paste0(dcf[1, "Package"], "_", dcf[1, "Version"], ".tar.gz")

url <- remotes:::download_version_url("remotes", "2.5.0", repos, type)
stopifnot(identical(basename(url), base))

sentence <- paste0(
  "download_version(\"remotes\", \"2.5.0\", repos = \"https://cloud.r-project.org\", type = \"source\") downloads ",
  base,
  "."
)
writeLines(sentence, file.path(out_dir, "download_version-r.txt"))

dest <- file.path(tempdir(), "dv")
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  remotes:::download(path = dest, url = url)
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}

cat(sprintf("{\"basename\":\"%s\",\"median_ms\":%.17g}\n", base, median(elapsed) * 1000))
