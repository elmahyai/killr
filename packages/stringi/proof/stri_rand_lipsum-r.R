suppressPackageStartupMessages(library(stringi))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")
suppressPackageStartupMessages(library(jsonlite))


x <- stri_rand_lipsum(2, TRUE)
writeLines(
  paste0("stri_rand_lipsum(2, TRUE) returns ", length(x), " paragraphs."),
  "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_rand_lipsum-r.txt"
)

one <- function() {
  drawn <- stri_rand_lipsum(2, TRUE)
  list(
    n = length(drawn),
    start = startsWith(drawn[[1]], "Lorem ipsum dolor sit amet"),
    endings = all(endsWith(drawn, ".")),
    no_newline = !any(grepl("\n", drawn, fixed = TRUE))
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
