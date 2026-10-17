.libPaths(c(path.expand("~/R/library"), .libPaths()))
suppressPackageStartupMessages(library(remotes))
stopifnot(packageVersion("remotes") == "2.5.0")

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- normalizePath(sub("^--file=", "", file_arg[[1]]))
out_dir <- file.path(dirname(script), "..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

expect_error <- function(expr, expected) {
  got <- tryCatch(eval(expr, envir = parent.frame()), error = function(e) conditionMessage(e))
  if (!identical(got, expected)) {
    stop(sprintf("expected [%s] got [%s]", expected, got), call. = FALSE)
  }
}

os_choices <- c("ubuntu", "centos", "redhat", "opensuse", "sle")
os_msg <- tryCatch(match.arg("foo", os_choices), error = function(e) conditionMessage(e))
ub_msg <- tryCatch(
  match.arg("1", c("14.04", "16.04", "18.04", "20.04", "22.04")),
  error = function(e) conditionMessage(e)
)
curl_msg <- "`curl` must be on the `PATH`."
split_msg <- "If os_release is missing, os must consist of name and release."

expect_error(quote(system_requirements("foo", "1")), os_msg)
expect_error(quote(system_requirements("ubuntu", "1")), ub_msg)
expect_error(quote(system_requirements("ubuntu", "2")), ub_msg)
expect_error(quote(system_requirements("ubuntu")), split_msg)
expect_error(quote(system_requirements("ubuntu-")), split_msg)
expect_error(quote(system_requirements("ubuntu-16.04-extra")), split_msg)
expect_error(quote(system_requirements("-16.04")), os_msg)
expect_error(quote(system_requirements("foo-bar")), os_msg)
expect_error(quote(system_requirements("ubuntu", "16.04", curl = "")), curl_msg)
expect_error(quote(system_requirements("foo", "1", curl = "")), os_msg)
expect_error(quote(system_requirements("u", "16", curl = "")), curl_msg)
expect_error(quote(system_requirements("ubuntu-16.04", curl = "")), curl_msg)
expect_error(quote(system_requirements("not-a-package-dir", "16.04")), os_msg)
expect_error(
  quote(system_requirements("ubuntu", "16.04", "not-a-package-dir")),
  "`not-a-package-dir` must contain a package."
)

make_pkg <- function(text) {
  pkg <- tempfile()
  dir.create(pkg)
  writeLines(text, file.path(pkg, "DESCRIPTION"))
  pkg
}

lib <- make_pkg("Package: testPkg\nSystemRequirements: libcurl")
empty <- make_pkg("Package: testPkg")
bad <- make_pkg("Not parsable")

one <- function() system_requirements("ubuntu", "16.04", lib)
value <- one()
stopifnot(identical(value, "apt-get install -y libcurl4-openssl-dev"))
stopifnot(identical(
  system_requirements("redhat", "7", lib),
  "yum install -y libcurl-devel"
))
stopifnot(identical(system_requirements("ubuntu", "16.04", empty), character()))
expect_error(
  quote(system_requirements("ubuntu", "16.04", bad)),
  "Could not parse DESCRIPTION: Bad line: 'Not parsable\\n' has no ':'"
)

sentence <- paste0(
  "system_requirements(\"ubuntu\", \"16.04\") for SystemRequirements: libcurl returns \"",
  value,
  "\"."
)
writeLines(sentence, file.path(out_dir, "system_requirements-r.txt"))

elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  got <- one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
  stopifnot(identical(got, value))
}

json_escape <- function(x) {
  x <- gsub("\\", "\\\\", x, fixed = TRUE)
  x <- gsub("\"", "\\\"", x, fixed = TRUE)
  paste0("\"", x, "\"")
}
cat(sprintf(
  "{\"value\":[%s],\"median_ms\":%.17g}\n",
  paste(vapply(value, json_escape, ""), collapse = ","),
  median(elapsed) * 1000
))
