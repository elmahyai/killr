suppressPackageStartupMessages(library(stringi))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")
suppressPackageStartupMessages(library(jsonlite))


x <- stri_rand_shuffle("abcd")
writeLines(
  paste0("stri_rand_shuffle('abcd') keeps ", nchar(x), " characters."),
  "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_rand_shuffle-r.txt"
)

one <- function() {
  drawn <- stri_rand_shuffle(c("abcd", NA, ""))
  list(
    same = identical(sort(utf8ToInt(drawn[[1]])), sort(utf8ToInt("abcd"))),
    na = is.na(drawn[[2]]),
    empty = identical(drawn[[3]], "")
  )
}

value <- one()
elapsed <- numeric(20)
for (i in seq_len(20)) {
  t0 <- as.numeric(Sys.time())
  one()
  elapsed[[i]] <- as.numeric(Sys.time()) - t0
}
cat(paste0(as.character(toJSON(list(value = value, median_ms = median(elapsed) * 1000), auto_unbox = TRUE, na = "null", digits = 16)), "\n"))
