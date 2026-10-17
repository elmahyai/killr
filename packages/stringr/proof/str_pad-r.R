.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(stringr))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(as.character(packageVersion("stringr")) == "1.6.0")
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")
options(warn = 1)

ex <- capture.output({
print(rbind(
  str_pad("hadley", 30, "left"),
  str_pad("hadley", 30, "right"),
  str_pad("hadley", 30, "both")
))
print(str_pad(c("a", "abc", "abcdef"), 10))
print(str_pad("a", c(5, 10, 20)))
print(str_pad("a", 10, pad = c("-", "_", " ")))
print(str_pad("hadley", 3))
})
writeLines(ex, "/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_pad-r.txt")

one <- function() {
  list(
    left = str_pad("had", 10, "left"),
    right = str_pad("had", 10, "right"),
    both = str_pad("had", 10, "both"),
    vec = str_pad(c("a", "abc", "abcdef"), 10),
    widths = str_pad("a", c(5, 10, 20)),
    pads = str_pad("a", 10, pad = c("-", "_", " ")),
    short = str_pad("hadley", 3),
    cjk = str_pad("\u4e2d", 6, "both"),
    length = str_pad("\u4e2d", 5, "both", use_width = FALSE),
    na = str_pad(c("a", NA), c(3, NA)),
    empty = str_pad(character(0), 10)
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
