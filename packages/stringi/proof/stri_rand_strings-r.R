suppressPackageStartupMessages(library(stringi))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")
suppressPackageStartupMessages(library(jsonlite))


x <- stri_rand_strings(4, 5, "[a-z]")
writeLines(
  paste0(
    "stri_rand_strings(4, 5, '[a-z]') returns ", length(x),
    " strings of length ", paste(nchar(x), collapse = ", "), "."
  ),
  "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_rand_strings-r.txt"
)

one <- function() {
  drawn <- stri_rand_strings(4, c(3, 5), c("[0-9]", "[abc]"))
  list(
    n = length(drawn),
    lengths = nchar(drawn),
    digits = all(grepl("^[0-9]{3}$", drawn[c(1, 3)])),
    letters = all(grepl("^[abc]{5}$", drawn[c(2, 4)])),
    empty_n = length(stri_rand_strings(0, 3)),
    na_length = is.na(stri_rand_strings(1, NA_integer_))
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
