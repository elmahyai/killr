.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(stringr))
if (as.character(packageVersion("stringr")) != "1.6.0") stop("expected stringr 1.6.0")

args <- commandArgs(trailingOnly = FALSE)
file_arg <- grep("^--file=", args, value = TRUE)
script <- normalizePath(sub("^--file=", "", file_arg[[1]]))
out_dir <- file.path(dirname(script), "..", "docs", "output")
dir.create(out_dir, recursive = TRUE, showWarnings = FALSE)
writeLines(
  c(
    str_interp(
      "One value, ${value1}, and then another, ${value2*2}.",
      list(value1 = 10, value2 = 20)
    ),
    str_interp(
      "User ${user_name} (account $[08d]{account}) has $$[.2f]{amount}.",
      list(user_name = "smbache", account = 1337, amount = 6.656)
    )
  ),
  file.path(out_dir, "str_interp-r.txt")
)

one <- function() {
  c(
    str_interp(
      "One value, ${value1}, and then another, ${value2*2}.",
      list(value1 = 10, value2 = 20)
    ),
    str_interp(
      "User ${user_name} (account $[08d]{account}) has $$[.2f]{amount}.",
      list(user_name = "smbache", account = 1337, amount = 6.656)
    ),
    str_interp(
      c(
        "This particular line is so long that it is hard to write ",
        "without breaking the ${max_char}-char barrier!"
      ),
      list(max_char = 80)
    )
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
