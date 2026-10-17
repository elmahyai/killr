.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(stringr))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(as.character(packageVersion("stringr")) == "1.6.0")
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")
options(warn = 1)

ex <- capture.output({
x <- "This string is moderately long"
print(rbind(
  str_trunc(x, 20, "right"),
  str_trunc(x, 20, "left"),
  str_trunc(x, 20, "center")
))
})
writeLines(ex, "/home/ahmed/killr_projects/killr/packages/stringr/docs/output/str_trunc-r.txt")

one <- function() {
  list(
    right = str_trunc("This string is moderately long", 20, "right"),
    left = str_trunc("This string is moderately long", 20, "left"),
    center = str_trunc("This string is moderately long", 20, "center"),
    c4 = str_trunc("This string is moderately long", 4, "center"),
    c5 = str_trunc("This string is moderately long", 5, "center"),
    c3 = str_trunc("This string is moderately long", 3, "center"),
    na = str_trunc(c("foobar", NA), 5),
    vec = str_trunc(c("abcd", "abcde", "abcdef"), 5),
    dots = str_trunc(c("", "a", "aa", "aaa", "aaaa", "aaaaaaa"), 4, "center", ".."),
    emoji = str_trunc("a\U0001F600bcdef", 5),
    empty = str_trunc(character(0), 4)
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
