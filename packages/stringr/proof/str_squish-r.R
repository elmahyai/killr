.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(stringr))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(as.character(packageVersion("stringr")) == "1.6.0")
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")
options(warn = 1)

ex <- capture.output({
print(str_squish("  String with trailing,  middle, and leading white space\t"))
print(str_squish("\n\nString with excess,  trailing and leading white   space\n\n"))
})
writeLines(ex, "/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_squish-r.txt")

one <- function() {
  list(
    tabs = str_squish("ab\t\tc\t"),
    middle = str_squish("  String with trailing,  middle, and leading white space\t"),
    nl = str_squish("\n\nString with excess,  trailing and leading white   space\n\n"),
    na = str_squish(NA_character_),
    empty = str_squish(character(0))
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste0(as.character(toJSON(list(value = value, median_ms = unbox(median(elapsed) * 1000)), auto_unbox = FALSE, na = "null", digits = 16)), "\n"))
