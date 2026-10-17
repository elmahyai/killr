suppressPackageStartupMessages(library(stringi))
stopifnot(as.character(packageVersion("stringi")) == "1.8.9")
suppressPackageStartupMessages(library(jsonlite))


s <- c(
  "Lorem ipsum dolor sit amet, consectetur adipisicing elit.",
  "nibh augue, suscipit a, scelerisque sed, lacinia in, mi.",
  "Cras vel lorem. Etiam pellentesque aliquet tellus.",
  ""
)
x <- stri_stats_general(s)
writeLines(
  paste0("stri_stats_general(s)$Lines returns ", x["Lines"], " and Chars returns ", x["Chars"], "."),
  "/home/ahmed/killr_projects/killr/packages/stringi/docs/output/stri_stats_general-r.txt"
)

one <- function() {
  list(
    lorem = as.list(stri_stats_general(s)),
    na = as.list(stri_stats_general(c("a", NA, "  ", "\u00a0b")))
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
