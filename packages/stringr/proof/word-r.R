.libPaths(c("/home/ahmed/R/x86_64-pc-linux-gnu-library/4.5", .libPaths()))
suppressPackageStartupMessages(library(stringr))
suppressPackageStartupMessages(library(jsonlite))
stopifnot(as.character(packageVersion("stringr")) == "1.6.0")
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")
options(warn = 1)

ex <- capture.output({
sentences <- c("Jane saw a cat", "Jane sat down")
print(word(sentences, 1))
print(word(sentences, 2))
print(word(sentences, -1))
print(word(sentences, 2, -1))
print(word(sentences[1], 1:3, -1))
print(word(sentences[1], 1, 1:4))
str <- "abc.def..123.4568.999"
print(word(str, 1, sep = fixed("..")))
print(word(str, 2, sep = fixed("..")))
})
writeLines(ex, "/home/ahmed/killr_projects/killr/packages/stringr/docs/output/word-r.txt")

one <- function() {
  list(
    first = word(c("Jane saw a cat", "Jane sat down"), 1),
    second = word(c("Jane saw a cat", "Jane sat down"), 2),
    last = word(c("Jane saw a cat", "Jane sat down"), -1),
    span = word(c("Jane saw a cat", "Jane sat down"), 2, -1),
    starts = word("Jane saw a cat", 1:3, -1),
    ends = word("Jane saw a cat", 1, 1:4),
    sep1 = word("abc.def..123.4568.999", 1, sep = fixed("..")),
    sep2 = word("abc.def..123.4568.999", 2, sep = fixed("..")),
    past = word("a b c", 4),
    far = word("walk the moon", -5, -1),
    double = word("a  b", 1:3),
    zero = word("a b", 0),
    blank = word("", 1),
    na = word(c("a b", NA), 1),
    nastart = word("a b c", NA_integer_),
    regex = word("a-b-c", 2, sep = "-"),
    coll = word("a b c", 2, sep = coll(" ")),
    empty = word(character(0))
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
