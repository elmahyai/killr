.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(stringr))
if (as.character(packageVersion("stringr")) != "1.6.0") stop("expected stringr 1.6.0")

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- normalizePath(sub("^--file=", "", file_arg[[1]]))
out_dir <- file.path(dirname(script), "..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)

name <- "Fred"
age <- 50
anniversary <- "Saturday, October 12, 1991"
writeLines(
  c(
    as.character(str_glue(
      "My name is {name}, ",
      "my age next year is {age + 1}, ",
      "and my anniversary is {anniversary}."
    )),
    as.character(str_glue("My name is {name}, not {{name}}."))
  ),
  file.path(out_dir, "str_glue-r.txt")
)

one <- function() {
  name <- "Fred"
  age <- 50
  anniversary <- "Saturday, October 12, 1991"
  c(
    as.character(str_glue(
      "My name is {name}, ",
      "my age next year is {age + 1}, ",
      "and my anniversary is {anniversary}."
    )),
    as.character(str_glue("My name is {name}, not {{name}}."))
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(sprintf(
  '{"value":%s,"median_ms":%.17g}\n',
  jsonlite::toJSON(value, auto_unbox = FALSE, digits = 17, na = "null"),
  median(elapsed) * 1000
))
